using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using Microsoft.CognitiveServices.Speech;
using Microsoft.CognitiveServices.Speech.Audio;
using Microsoft.CognitiveServices.Speech.Translation;

namespace NeosTextTranslator
{
    public class ContinuousTranslator
    {
        // recognizer
        private TranslationRecognizer recognizer;

        public async Task StartRecognition(IEnumerable<string> targetLanguages)
        {            
            // create SpeechTranslationConfig using Azure settings defined in data model
            var speechConfig = SpeechTranslationConfig.FromSubscription(NeosTranslateDataModel.Instance.AzureSubscriptionKey, NeosTranslateDataModel.Instance.AzureRegion);

            // configure input language from data model and translation target languages using list passed in to this function
            // Note: trying to translate to multiple languages causes a generic exception (with no name or details), so for now don't try to use the multiple-target-languages feature.
            speechConfig.SpeechRecognitionLanguage = NeosTranslateDataModel.TRANSLATOR_INPUT_LANGUAGE;
            foreach(string lang in targetLanguages)
                speechConfig.AddTargetLanguage(lang);

            // create AudioConfig that reads audio from source defined in data model
            // this can be default microphone, microhone by name, speaker output, wav file, etc
            // see https://docs.microsoft.com/en-us/dotnet/api/microsoft.cognitiveservices.speech.audio.audioconfig?view=azure-dotnet
            var audioConfig = NeosTranslateDataModel.AUDIO_INPUT_SOURCE;

            // create recognizer, needs to be properly stopped / disposed elsewhere
            recognizer = new TranslationRecognizer(speechConfig, audioConfig);
            recognizer.Recognized += Recognizer_Recognized;
            recognizer.Canceled += Recognizer_Canceled;

            // Starts continuous recognition. Uses StopContinuousRecognitionAsync() to stop recognition.
            string targetLanguagesStr = targetLanguages.Aggregate((a, b) => a + ' ' + b);
            SystemMessage($"Starting continuous translation from {NeosTranslateDataModel.TRANSLATOR_INPUT_LANGUAGE} to {targetLanguagesStr}");
            await recognizer.StartContinuousRecognitionAsync().ConfigureAwait(false);
        }

        public async Task StopRecognition()
        {
            if(recognizer != null)
            {
                SystemMessage("Stopping continuous translation");
                await recognizer.StopContinuousRecognitionAsync().ConfigureAwait(false);
            }
        }

        private void Recognizer_Recognized(object sender, TranslationRecognitionEventArgs e)
        {
            if (e.Result.Reason == ResultReason.TranslatedSpeech)
            {
                // speech was successfully recognized and translated, output the recognized text and all translated text
                TextRecognized(e.Result.Text);
                foreach (var element in e.Result.Translations)
                    TextTranslated(element.Key, element.Value);
            }
            else if (e.Result.Reason == ResultReason.RecognizedSpeech)
            {
                // speech was recognized but could not be translated
                TextRecognized(e.Result.Text);
                SystemMessage("Speech could not be translated.");
            }
            else if (e.Result.Reason == ResultReason.NoMatch)
            {
                // speech could not be recognized
                SystemMessage("Speech could not be recognized.");
            }
        }

        private void Recognizer_Canceled(object sender, TranslationRecognitionCanceledEventArgs e)
        {
            SystemMessage($"CANCELED: Reason={e.Reason}");

            if (e.Reason == CancellationReason.Error)
            {
                SystemMessage($"CANCELED: ErrorCode={e.ErrorCode}");
                SystemMessage($"CANCELED: ErrorDetails={e.ErrorDetails}");
                SystemMessage($"CANCELED: Did you update the subscription info?");
            }
        }

        // writes a message out the to console and also adds it to the Neos message queue as a system message
        internal static void SystemMessage(string message)
        {
            Console.WriteLine(message);
            NeosTranslateDataModel.Instance.EnqueueSystemMessage(message);
        }

        // function called when text is recognized in the input language (successful speech recognitoin)
        // writes message to console and also adds it to the Neos message queue as recognized text
        internal static void TextRecognized(string text)
        {
            if (!string.IsNullOrWhiteSpace(text))
            {
                Console.WriteLine($"RECOGNIZED in '{NeosTranslateDataModel.TRANSLATOR_INPUT_LANGUAGE}': {text}");
                NeosTranslateDataModel.Instance.EnqueueRecognizedText(text);
            }
        }

        // function called when text is translated into one of the target languages (successful text translation)
        // writes message to console and also adds it to the Neos message queue as translted text
        internal static void TextTranslated(string language, string text)
        {
            if (!string.IsNullOrWhiteSpace(text))
            {
                Console.WriteLine($"    TRANSLATED into '{language}': {text}");
                NeosTranslateDataModel.Instance.EnqueueTranslatedText(text);
            }
        }

    }
}
