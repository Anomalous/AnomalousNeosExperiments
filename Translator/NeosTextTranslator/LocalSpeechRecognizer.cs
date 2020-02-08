using System;
using System.Collections.Generic;
using System.Linq;
using System.Speech.Recognition;
using System.Text;
using System.Threading.Tasks;

namespace NeosTextTranslator
{
    public class LocalSpeechRecognizer
    {
        private SpeechRecognitionEngine recognizer;

        public void StartListening()
        {
            StopListening();

            // create recognizer for specified locale
            recognizer = new SpeechRecognitionEngine(new System.Globalization.CultureInfo(NeosTranslateDataModel.TRANSLATOR_INPUT_LANGUAGE));

            // select and load a dictation grammar, in this case a general-purpose dictation grammar
            recognizer.LoadGrammar(new DictationGrammar());

            // speech recognized or rejected events
            recognizer.SpeechRecognized += Recognizer_SpeechRecognized;
            recognizer.SpeechRecognitionRejected += Recognizer_SpeechRecognitionRejected;

            // listen on default microphone
            recognizer.SetInputToDefaultAudioDevice();

            // inform user
            ContinuousTranslator.SystemMessage("Starting local speech recognition");

            // start async continuous speech recognition
            recognizer.RecognizeAsync(RecognizeMode.Multiple);
        }

        public void StopListening()
        {
            if (recognizer != null)
            {
                ContinuousTranslator.SystemMessage("Stopping local speech recognition");

                recognizer.RecognizeAsyncCancel();
                recognizer.Dispose();
                recognizer = null;
            }
        }

        private void Recognizer_SpeechRecognized(object sender, SpeechRecognizedEventArgs e)
        {
            ContinuousTranslator.TextRecognized(e.Result.Text);
        }

        private void Recognizer_SpeechRecognitionRejected(object sender, SpeechRecognitionRejectedEventArgs e)
        {
            ContinuousTranslator.SystemMessage("Speech could not be recognized.");
        }

        

        
    }

 
}
