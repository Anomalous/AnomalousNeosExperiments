using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Text;
using System.Threading;
using System.Threading.Tasks;


// Program demonstrating real-time speech translation in Neos VR.
// This is just a proof of concept, not a fully fledged program.

// It uses Azure APIs to monitor the microphone, perform speech recognition, and translate the recogized text.
// You do need an Azure account to use this program. Settings are in NeosTranslateDataModel.cs.
// The recognized text and translated text are stored in a queue and made available for Neos to read using a simple web server.
// The web server also receives input from Neos to select the target language(s) for translation.

// This program is largely a combination of different examples from Microsoft,
// with little bit of glue code and some formatting for the data to be sent to Neos.
// Here are some of the examples that were used:
// Single shot translation: https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/quickstarts/translate-speech-to-text?pivots=programming-language-csharp&tabs=dotnet
// Continuous translation: https://github.com/Azure-Samples/cognitive-services-speech-sdk/blob/master/samples/csharp/sharedcontent/console/translation_samples.cs
// HttpListener: https://docs.microsoft.com/en-us/dotnet/api/system.net.httplistener?view=netframework-4.8


namespace NeosTextTranslator
{
    class Program
    {
        public static async Task Main(string[] args)
        {
            var dm = NeosTranslateDataModel.Instance;

            Console.WriteLine("Program starting, press Enter to shut down at any time.");
            Console.WriteLine("");

            // start web server listening for Neos requests
            // note that translator will automatically start when a language is specified by Neos
            dm.HttpListener.StartListening();

            // wait for Enter to be pressed
            Console.ReadLine();

            // close down translator and web server
            // may not be necessary since program is shutting down at this point anyway
            await dm.Translator.StopRecognition();
            dm.HttpListener.StopListening();
        }

    }
}
