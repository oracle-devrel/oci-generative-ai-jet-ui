import "preact";
import { useState, useRef, useEffect, useContext } from "preact/hooks";
import "md-wrapper/loader";
import "ojs/ojtoolbar";
import "oj-c/file-picker";
import "oj-c/message-toast";
import "oj-c/input-text";
import "oj-c/progress-bar";
import "oj-c/button";
import "ojs/ojvalidationgroup";
import "oj-sp/ai-button/loader"
import { ojValidationGroup } from "ojs/ojvalidationgroup";
import { CFilePickerElement } from "oj-c/file-picker";
import { CInputTextElement } from "oj-c/input-text";
import { CButtonElement } from "oj-c/button";
import MutableArrayDataProvider = require("ojs/ojmutablearraydataprovider");
import { ConvoCtx } from "../app";

declare global {
  namespace preact.JSX {
    interface IntrinsicElements {
      "md-wrapper": any;
    }
  }
}
type Props = {
  fileChanged: (file: ArrayBuffer) => void;
  clear: () => void;
  prompt: (val: string) => void;
  summaryChanged: (summary: string) => void;
  summary: string;
  modelId: string | null;
  backendType: any;
};
const protocol = window.location.protocol === "http:" ? "ws://" : "wss://";
const hostname =
  window.location.hostname === "localhost"
    ? "localhost:8080"
    : window.location.hostname;
const serviceRootURL = `${protocol}${hostname}`;
const acceptArr: string[] = ["application/pdf", "*.pdf", "text/plain", "*.txt"];
const messages: { id: number; severity: string; summary: string }[] = [];
const FILE_SIZE = 120000;

export const Summary = ({
  fileChanged,
  clear,
  prompt,
  summaryChanged,
  summary,
  modelId,
  backendType,
}: Props) => {
  const conversationId = useContext(ConvoCtx);
  const [invalidMessage, setInvalidMessage] = useState<string | null>(null);
  const [summaryPrompt, setSummaryPrompt] = useState<string>("");
  const [summaryResults, setSummaryResults] = useState<string | null>(summary);
  const [fileNames, setFileNames] = useState<string[] | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [messages, setMessages] = useState<object[]>([]);
  const [pdfFile, setPDFFile] = useState<ArrayBuffer>();
  const [loading, setLoading] = useState<boolean>(false);
  const invalidFiles = useRef<string[]>([]);
  const valGroupRef = useRef<ojValidationGroup>(null);
  const promptInputRef = useRef<CInputTextElement<string | null>>(null);

  // Message toast related methods
  const closeMessage = () => {
    setMessages([]);
    invalidFiles.current = [];
    setFileNames(null);
  };

  const messagesDP = new MutableArrayDataProvider<string, {}>(messages, {
    keyAttributes: "id",
  });

  // Prompt input related methods
  const submitPrompt = (event: CInputTextElement.valueChanged<string>) => {
    let tempStr = event.detail.value
      ? event.detail.value
      : "";
    setSummaryPrompt(tempStr);
    prompt(tempStr);
  };

  const sendToJavaBackend = async (file: File, prompt: string) => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("/api/upload", {
      // const res = await fetch("http://localhost:5173/api/upload", {
      method: "POST",
      mode: "cors",
      referrerPolicy: "strict-origin-when-cross-origin",
      body: formData,
      headers: { conversationID: conversationId, modelId: modelId ? modelId : "", contextStr: summaryPrompt },
    });
    console.log("Response: ", res);
    const responseData = await res.json();
    const { content, errorMessage } = responseData;
    if (errorMessage.length) {
      // setErrorMessage(errorMessage);
      // setShowError(true);
    } else {
      console.log("Response: ", content);
      setSummaryResults(content);
      summaryChanged(content);
    }
  };
  // FilePicker related methods
  const selectListener = async (event: CFilePickerElement.ojSelect) => {
    setInvalidMessage("");
    const files: FileList = event.detail.files;
    const filesArray: File[] = Array.from(files);
    let names = filesArray.map((file: File) => {
      return file?.name;
    });

    if (backendType === "java") {
      setFile(files[0]);
      setFileNames(names);
    } else {
      const fr = new FileReader();
      let ab = new ArrayBuffer(200000000);
      fr.onload = (ev: ProgressEvent<FileReader>) => {
        let ab = fr.result;
        setPDFFile(ab as ArrayBuffer);
      };
      fr.readAsArrayBuffer(files[0]);
      setFileNames(names);
    }
  };

  const buildSummaryData = (rawData: ArrayBuffer) => {
    const metaJson = {
      type: "summary",
      msgPrompt: summaryPrompt,
    };

    // _must_ do this to encode as a ArrayBuffer / Uint8Array
    // credit to Ben Wills and this article for inspiration with the below code.
    // https://enomem.io/sending-and-receiving-binary-files-via-websockets/
    const enc = new TextEncoder(); // always utf-8, Uint8Array()
    const buf1 = enc.encode(JSON.stringify(metaJson));
    const buf2 = enc.encode("\r\n\r\n");
    const buf3 = rawData;

    let sendData = new Uint8Array(
      buf1.byteLength + buf2.byteLength + buf3.byteLength
    );
    sendData.set(new Uint8Array(buf1), 0);
    sendData.set(new Uint8Array(buf2), buf1.byteLength);
    sendData.set(new Uint8Array(buf3), buf1.byteLength + buf2.byteLength);

    return sendData;
  };

  const invalidListener = (event: CFilePickerElement.ojInvalidSelect) => {
    setFileNames([]);
    const promise = event.detail.until;

    if (promise) {
      promise.then(() => {
        setInvalidMessage("");
      });
    }
  };
  const beforeSelectListener = (event: CFilePickerElement.ojBeforeSelect) => {
    const accept: (acceptPromise: Promise<void>) => void = event.detail.accept;
    const files: FileList = event.detail.files;
    let file: File;
    let tempArray: Array<string> = [];

    for (let i = 0; i < files.length; i++) {
      file = files[i];
      // Cohere has a character limit of ~100kb so we are restricting it here as well.
      // We can use LangChain in this area to support larger files.
      if (file.size > FILE_SIZE) {
        tempArray.push(file.name);
        invalidFiles.current = tempArray;
      }
    }

    if (invalidFiles.current.length === 0) {
      accept(Promise.resolve());
    } else {
      if (invalidFiles.current.length === 1) {
        let temp: Array<object> = [];
        temp.push({
          id: 0,
          severity: "Error",
          summary:
            "File " +
            invalidFiles.current[0] +
            ` is too big. The maximum size is ${FILE_SIZE / 1000}KB.`,
        });
        setMessages(temp);
      } else {
        const fileNames = invalidFiles.current.join(", ");
        let temp: Array<object> = [];
        temp.push({
          id: 0,
          severity: "Error",
          summary:
            "These files are too big: " +
            fileNames +
            `. The maximum size is ${FILE_SIZE / 1000}KB.`,
        });
        setMessages(temp);
      }

      accept(Promise.reject(messages));
    }
  };

  useEffect(() => {
    if (summaryResults !== "") setLoading(!loading);
  }, [summaryResults]);

  useEffect(() => {
    setSummaryResults(summary);
  }, [summary]);

  useEffect(() => {
    return () => {
      clearSummarization();
    };
  }, []);

  const _checkValidationGroup = () => {
    const tracker = valGroupRef.current as ojValidationGroup;
    if (tracker.valid === "valid") {
      return true;
    } else {
      // show messages on all the components that are invalidHiddden, i.e., the
      // required fields that the user has yet to fill out.
      tracker.showMessages();
      tracker.focusOn("@firstInvalidShown");
      return false;
    }
  };

  // Summarize methods
  const summarizeFile = (event: CButtonElement.ojAction) => {
    const valid = _checkValidationGroup();
    if (valid) {
      clear();
      console.log("Calling websocket API to process PDF");
      console.log("Filename: ", fileNames);
      console.log("Prompt: ", summaryPrompt);
      if (backendType === "python") {
        fileChanged(buildSummaryData(pdfFile as ArrayBuffer));
      } else {
        sendToJavaBackend(file!, summaryPrompt);
      }
      setLoading(true);
    }
  };
  const clearSummarization = () => {
    promptInputRef.current?.reset();
    setFileNames(null);
    clear();
    setLoading(false);
  };

  return (
    <>
      <oj-c-message-toast
        data={messagesDP}
        onojClose={closeMessage}
      ></oj-c-message-toast>

      <div class="oj-flex-item oj-sm-margin-4x">
        <h1>Document Summarization</h1>
        <div class="oj-typography-body-md oj-sm-padding-1x-bottom">
          Upload a PDF/TXT file
        </div>
        <oj-validation-group ref={valGroupRef}>
          <oj-c-file-picker
            id="filepickerPdf"
            accept={acceptArr}
            selectionMode="single"
            onojSelect={selectListener}
            onojInvalidSelect={invalidListener}
            onojBeforeSelect={beforeSelectListener}
            secondaryText={`Maximum file size is ${FILE_SIZE / 1000
              }KB per PDF or TXT file.`}
          ></oj-c-file-picker>

          <oj-c-input-text
            id="promptInput"
            ref={promptInputRef}
            class="oj-sm-width-full oj-md-width-1/2 oj-sm-margin-4x-top oj-sm-margin-4x-bottom"
            labelHint="Add context of how you want to summarize this file (optional)"
            labelEdge="top"
            onvalueChanged={submitPrompt}
          ></oj-c-input-text>
        </oj-validation-group>
        {invalidFiles.current.length !== 1 && fileNames && (
          <>
            <div class="oj-sm-margin-4x-top">
              <span class="oj-typography-bold">File: </span>
              {fileNames}
            </div>
            <oj-toolbar
              id="consrolsToolbar"
              class="oj-sm-margin-10x-top"
              aria-label="summarization toolbar"
              aria-controls="summaryContent"
            >
              <oj-sp-ai-button onspAction={summarizeFile}>
              </oj-sp-ai-button>
              <oj-c-button
                label="Summarize"
                onojAction={summarizeFile}
              ></oj-c-button>
              <oj-c-button
                label="Clear"
                onojAction={clearSummarization}
              ></oj-c-button>
            </oj-toolbar>
          </>
        )}
        {invalidFiles.current.length !== 1 && fileNames && loading && (
          <>
            <div class="oj-sm-margin-4x oj-typography-subheading-md">
              Loading summary
            </div>
            <oj-c-progress-bar
              class="oj-sm-margin-4x oj-sm-width-full oj-md-width-1/2"
              value={-1}
            ></oj-c-progress-bar>
          </>
        )}
        {invalidFiles.current.length !== 1 && fileNames && summary && (
          <div
            id="summaryContent"
            class="oj-panel oj-sm-width-full oj-color-invert oj-sm-padding-4x oj-sm-margin-6x-top"
            style="background-color: var(--oj-sp-header-welcome-banner-background-color);"
          >
            <md-wrapper
              id="TestingOne"
              class="oj-sm-width-full"
              markdown={summaryResults}
            />
          </div>
        )}
      </div>
    </>
  );
};
