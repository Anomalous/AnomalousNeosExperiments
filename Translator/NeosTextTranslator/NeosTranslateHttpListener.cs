using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Net;
using System.Text;
using System.Threading.Tasks;

namespace NeosTextTranslator
{
    public class NeosTranslateHttpListener
    {
        private HttpListener listener = new HttpListener();
        private bool cancelRequested = false;

        public NeosTranslateHttpListener()
        {

        }

        public async void StartListening()
        {
            // stop, re-configure, (re-)start the HttpListener
            listener.Stop();
            listener.Prefixes.Clear();
            listener.Prefixes.Add(NeosTranslateDataModel.HTTP_LISTENER_URL);
            listener.Start();

            try
            {
                while (!cancelRequested)
                {
                    // asyncronously wait for connection from Neos
                    // since we use await and don't specify ConfigureAwait(false), we should end up in the same execution context when this resumes executing
                    // GetContextAsync doesn't accept a cancellation token for some reason?
                    var context = await listener.GetContextAsync();
                    var request = context.Request;

                    Console.WriteLine("Request for " + request.RawUrl);

                    // examine URL to see what command is issued
                    if (request.RawUrl.StartsWith("/SetLanguage"))
                        setLanguage(context, request.QueryString["Language"]);
                    else if (request.RawUrl.StartsWith("/AddLanguage"))
                        addLanguage(context, request.QueryString["Langauge"]);
                    else if (request.RawUrl.StartsWith("/RemoveLanguage"))
                        removeLanguage(context, request.QueryString["Language"]);
                    else if (request.RawUrl.StartsWith("/GetMessages"))
                        sendMessagesFromQueue(context);
                    else
                        sendText(context, $"Unknown Command: {request.RawUrl}");
                }
            }
            catch(HttpListenerException)
            {
                // occurs when thread is shut down
            }

            listener.Stop();                // probably redundant
            cancelRequested = false;        // reset
        }

        public void StopListening()
        {
            // hopefully this cancels pending GetContextAsyc methods
            cancelRequested = true;
            listener.Stop();
        }

        private void sendText(HttpListenerContext context, string text)
        {
            if (string.IsNullOrWhiteSpace(text))
                text = "";

            Console.WriteLine($"Sending text {text}");

            // construct response
            var response = context.Response;
            string responseStr = text.ToString();
            byte[] responseBytes = Encoding.UTF8.GetBytes(responseStr);

            // write response into response stream
            response.ContentLength64 = responseBytes.Length;
            using (var responseStream = response.OutputStream)
            {
                responseStream.Write(responseBytes, 0, responseBytes.Length);
            }
        }

        private void sendMessagesFromQueue(HttpListenerContext context)
        {
            sendText(context, NeosTranslateDataModel.Instance.GetAllQueuedMessages());
        }

        private void setLanguage(HttpListenerContext context, string newLanguage)
        {
            Console.WriteLine($"Setting translation target to {newLanguage}");
            NeosTranslateDataModel.Instance.SetSingleTranslationTarget(newLanguage);
            sendText(context, "OK");
        }

        private void addLanguage(HttpListenerContext context, string newLanguage)
        {
            Console.WriteLine($"Adding translation target {newLanguage}");
            NeosTranslateDataModel.Instance.AddTranslationTarget(newLanguage);
            sendText(context, "OK");
        }

        private void removeLanguage(HttpListenerContext context, string newLanguage)
        {
            Console.WriteLine($"Removing translation target {newLanguage}");
            NeosTranslateDataModel.Instance.RemoveTranslationTarget(newLanguage);
            sendText(context, "OK");
        }
    }
}
