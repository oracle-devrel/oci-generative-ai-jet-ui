import "preact";
import { useState, useRef } from "preact/hooks";
import "ojs/ojtoolbar";
import "oj-c/file-picker";
import "oj-c/message-toast";
import "oj-c/input-text";
import "oj-c/button";
import { CFilePickerElement } from "oj-c/file-picker";
import { CInputTextElement } from "oj-c/input-text";
import { CButtonElement } from "oj-c/button";
import MutableArrayDataProvider = require("ojs/ojmutablearraydataprovider");

type Props = {
  fileChanged: (file: ArrayBuffer) => null;
};

const acceptArr: string[] = ["application/pdf", "*.pdf"];
const messages: { id: number; severity: string; summary: string }[] = [];

export const Summary = ({ fileChanged }: Props) => {
  const [invalidMessage, setInvalidMessage] = useState<string | null>(null);
  const [fileNames, setFileNames] = useState<string[] | null>(null);
  const [messages, setMessages] = useState<object[]>([]);
  const [pdfFile, setPDFFile] = useState<ArrayBuffer>();
  const invalidFiles = useRef<string[]>([]);

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
    console.log("prompt: ", event.detail.value);
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

      if (file.size > 200000000) {
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
            " is too big. The maximum size is 200MB.",
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
            ". The maximum size is 200MB.",
        });
        setMessages(temp);
      }

      accept(Promise.reject(messages));
    }
  };

  // Summarize methods
  const summarizeFile = (event: CButtonElement.ojAction) => {
    console.log("calling websocket API to process PDF");
    fileChanged(pdfFile as ArrayBuffer);
  };
  const clearSummarization = () => {
    setFileNames(null);
  };

  return (
    <>
      <oj-c-message-toast
        data={messagesDP}
        onojClose={closeMessage}
      ></oj-c-message-toast>

      <div class="oj-flex-item oj-sm-margin-4x">
        <h1>Document Summarization</h1>
        <oj-c-input-text
          id="promptInput"
          aria-label="enter document summary prompt"
          class="oj-sm-width-full oj-md-width-1/2 oj-sm-margin-4x-bottom"
          labelHint="Enter the document summary prompt"
          labelEdge="top"
          onvalueChanged={submitPrompt}
        ></oj-c-input-text>
        <div class="oj-text-color-secondary oj-typography-body-sm oj-sm-padding-1x-bottom">
          Upload a PDF file
        </div>
        <oj-c-file-picker
          id="filepickerPdf"
          accept={acceptArr}
          selectionMode="single"
          onojSelect={selectListener}
          onojInvalidSelect={invalidListener}
          onojBeforeSelect={beforeSelectListener}
          secondaryText="Maximum file size is 200MB per PDF file."
        ></oj-c-file-picker>

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
            <div id="summaryContent" class="oj-panel oj-sm-width-full">
              {"Markdown content would go in here"}
            </div>
          </>
        )}
      </div>
    </>
  );
};
