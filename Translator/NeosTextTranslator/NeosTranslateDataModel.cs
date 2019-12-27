using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using Microsoft.CognitiveServices.Speech.Audio;

namespace NeosTextTranslator
{
    public sealed class NeosTranslateDataModel
    {
        #region Singleton stuff

        private static readonly Lazy<NeosTranslateDataModel> instance = new Lazy<NeosTranslateDataModel>(() => new NeosTranslateDataModel());

        public static NeosTranslateDataModel Instance { get { return instance.Value; } }

        private NeosTranslateDataModel() { }

        #endregion

        #region Constants

        // Azure subscription key; you must input your own here or else voice recognition and translation will not work!
        // Info on creating an Azure account and setting up a speech resource can be found here: 
        // https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/get-started
        public const string DEFAULT_AZURE_SUBSCRIPTION_KEY = "key goes here";

        // Region to use when connecting to Azure, goes along with subscription key
        public const string DEFAULT_AZURE_REGION = "westus";

        // langauge which translator will try to translate from
        // codes for supported languages: https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/language-support
        public const string TRANSLATOR_INPUT_LANGUAGE = "en-US";

        // audio input source to use
        // can be default microphone, microphone specified by name, speaker output, wav file, etc.
        // see https://docs.microsoft.com/en-us/dotnet/api/microsoft.cognitiveservices.speech.audio.audioconfig?view=azure-dotnet
        public static readonly AudioConfig AUDIO_INPUT_SOURCE = AudioConfig.FromDefaultMicrophoneInput();

        // URL and port where HttpLister will listen for connections from Neos
        // Note that on Widows 10 HttpListener only works on localhost unless you change some security settings using the netsh command
        public const string HTTP_LISTENER_URL = "http://localhost:8083/";

        // messages older than this are discarded instead of being sent to Neos
        // this is to avoid receiving a big chunk of cached messages if the translator has been running for a while without anything requesting the queued messages
        public static readonly TimeSpan MESSAGE_MAX_LIFETIME = TimeSpan.FromMinutes(5);

        #endregion

        // allow region and key to be set without re-compiling the program
        public string AzureRegion { get; set; } = DEFAULT_AZURE_REGION;
        public string AzureSubscriptionKey { get; set; } = DEFAULT_AZURE_SUBSCRIPTION_KEY;

        public ContinuousTranslator Translator { get; } = new ContinuousTranslator();
        public NeosTranslateHttpListener HttpListener { get; } = new NeosTranslateHttpListener();

        #region Message Queue

        // stores one message destined to be sent to Neos 
        public class MessageForNeos
        {
            // message age
            public DateTime CreationTime { get; } = DateTime.Now;
            public TimeSpan Age { get { return DateTime.Now - CreationTime; } }

            // message data
            public string MessageType { get; set; }                 // could be an enum instead of a string
            public string MessageData { get; set; }

            // ToString used to format message to send to Neos
            public override string ToString()
            {
                return $"{MessageType}: {MessageData}";
            }
        }

        // Queue that stores all messages available to Neos
        // Not 100% certain if ConcurrentQueue is required given that we're using async/await, 
        // but I think the speech recognizer callback methods may be executing from a thread pool in which case we do have to worry about synchronization
        public ConcurrentQueue<MessageForNeos> MessageQueue { get; } = new ConcurrentQueue<MessageForNeos>();

        // functions to enqueue messages to send to Neos
        public void EnqueueMessage(string type, string data)
        {
            // messages are only enqueued if they actually have data, otherwise they are discarded
            if (!string.IsNullOrEmpty(data))
                MessageQueue.Enqueue(new MessageForNeos() { MessageType = type, MessageData = data });
        }
        public void EnqueueSystemMessage(string msg) { EnqueueMessage("SystemMessage", msg); }
        public void EnqueueRecognizedText(string txt) { EnqueueMessage("RecognizedText", txt); }
        public void EnqueueTranslatedText(string txt) { EnqueueMessage("TranslatedText", txt); }

        // Function that pulls all enqueued messages out of the queue and composes them into one big string. Messages are separated by newline characters.
        // This is done because Neos runs Get requests on a timer; there's no way to stream the data into Neos AFAIK (except for plugins which break compatibility for anyone that doesn't have the same plugin installed).
        // Since we only get enqueued messages perhaps once per second, we might get behind if each request only returned one message.
        // We discard any messages that are too old to avoid a flood of cached messages when the translator has been running for a while but Neos hasn't been requesting messages.
        public string GetAllQueuedMessages()
        {
            StringBuilder sb = new StringBuilder();
            MessageForNeos msg;
            while(!MessageQueue.IsEmpty && MessageQueue.TryDequeue(out msg))
                if(msg.Age <= MESSAGE_MAX_LIFETIME)
                    sb.AppendLine(msg.ToString());
            return sb.ToString();
        }

        #endregion

        #region Translation Target Languages

        // list of languages that speech will be translated into
        private HashSet<string> TargetLanguages { get; } = new HashSet<string>();

        // add a language to the list of translation targets
        public void AddTranslationTarget(string language)
        {
            if(!TargetLanguages.Contains(language))
            {    
                TargetLanguages.Add(language);
                restartTranslator();
            }
        }

        // remove a language from the list of translation targets
        public void RemoveTranslationTarget(string language)
        {
            if (TargetLanguages.Contains(language))
            {
                TargetLanguages.Remove(language);
                restartTranslator();
            }
        }

        // set the translation target to only one language, removing all other that were previously present
        public void SetSingleTranslationTarget(string language)
        {
            if (TargetLanguages.Count == 1 && TargetLanguages.Contains(language))
                return;

            TargetLanguages.Clear();
            TargetLanguages.Add(language);
            restartTranslator();
        }

        // restart continuous translator to update its target language list
        // it might be possible to update the translator's target language list without stopping and restarting it, which would be desirable
        private async void restartTranslator()
        {
            await Translator.StopRecognition();
            await Translator.StartRecognition(TargetLanguages).ConfigureAwait(false);
        }

        #endregion

    }
}
