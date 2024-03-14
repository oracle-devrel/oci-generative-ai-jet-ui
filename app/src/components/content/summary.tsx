import "preact";
import { useState, useRef, useEffect } from "preact/hooks";
import "md-wrapper/loader";
import "ojs/ojtoolbar";
import "oj-c/file-picker";
import "oj-c/message-toast";
import "oj-c/input-text";
import "oj-c/progress-bar";
import "oj-c/button";
import "ojs/ojvalidationgroup";
import { ojValidationGroup } from "ojs/ojvalidationgroup";
import { CFilePickerElement } from "oj-c/file-picker";
import { CInputTextElement } from "oj-c/input-text";
import { CButtonElement } from "oj-c/button";
import MutableArrayDataProvider = require("ojs/ojmutablearraydataprovider");

declare global {
  namespace preact.JSX {
    interface IntrinsicElements {
      "md-wrapper": any;
    }
  }
}
type Props = {
  fileChanged: (file: ArrayBuffer) => void;
  summary: string | null;
  clear: () => void;
  prompt: (val: string) => void;
};

const acceptArr: string[] = ["application/pdf", "*.pdf"];
const messages: { id: number; severity: string; summary: string }[] = [];

export const Summary = ({ fileChanged, summary, clear, prompt }: Props) => {
  const [invalidMessage, setInvalidMessage] = useState<string | null>(null);
  const [summaryPrompt, setSummaryPrompt] = useState<string>("");
  const [fileNames, setFileNames] = useState<string[] | null>(null);
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
      : "Generate a summary";
    setSummaryPrompt(tempStr);
    prompt(tempStr);
  };

  // FilePicker related methods
  const selectListener = async (event: CFilePickerElement.ojSelect) => {
    setInvalidMessage("");
    const files: FileList = event.detail.files;
    const filesArray: File[] = Array.from(files);
    let names = filesArray.map((file: File) => {
      return file?.name;
    });

    const fr = new FileReader();
    let ab = new ArrayBuffer(200000000);
    fr.onload = (ev: ProgressEvent<FileReader>) => {
      let ab = fr.result;
      setPDFFile(ab as ArrayBuffer);
    };
    fr.readAsArrayBuffer(files[0]);
    setFileNames(names);
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
      // Cohere has a character limit of 100kb so we are restricting it here as well.
      if (file.size > 100000) {
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
            " is too big. The maximum size is 100KB.",
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
            ". The maximum size is 100KB.",
        });
        setMessages(temp);
      }

      accept(Promise.reject(messages));
    }
  };

  useEffect(() => {
    if (summary !== "") setLoading(!loading);
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
      fileChanged(buildSummaryData(pdfFile as ArrayBuffer));
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
          Upload a PDF file
        </div>
        <oj-validation-group ref={valGroupRef}>
          <oj-c-file-picker
            id="filepickerPdf"
            accept={acceptArr}
            selectionMode="single"
            onojSelect={selectListener}
            onojInvalidSelect={invalidListener}
            onojBeforeSelect={beforeSelectListener}
            secondaryText="Maximum file size is 100KB per PDF file."
          ></oj-c-file-picker>
          <oj-c-input-text
            id="promptInput"
            ref={promptInputRef}
            required
            aria-label="enter document summary prompt"
            class="oj-sm-width-full oj-md-width-1/2 oj-sm-margin-4x-top oj-sm-margin-4x-bottom"
            labelHint="Enter the document summary prompt"
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
          <div id="summaryContent" class="oj-panel oj-sm-width-full">
            <md-wrapper
              id="TestingOne"
              class="oj-sm-width-full"
              markdown={summary}
            />
          </div>
        )}
      </div>
    </>
  );
};
