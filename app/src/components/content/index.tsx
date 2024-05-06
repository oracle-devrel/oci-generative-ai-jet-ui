import { Chat } from "./chat";
import { Summary } from "./summary";
import { Simulation } from "./simulation";
import { Settings } from "./settings";
import "preact";
import "ojs/ojinputsearch";
import "oj-c/message-toast";
import "oj-c/drawer-popup";
import MutableArrayDataProvider = require("ojs/ojmutablearraydataprovider");
import { MessageToastItem } from "oj-c/message-toast";
import { InputSearchElement } from "ojs/ojinputsearch";
import { useState, useEffect, useRef } from "preact/hooks";
import * as Questions from "text!./data/questions.json";
import * as Answers from "text!./data/answers.json";

type ServiceTypes = "text" | "summary" | "sim";
type Chat = {
  id?: number;
  question?: string;
  answer?: string;
  loading?: string;
};
const Content = () => {
  const [update, setUpdate] = useState<Array<object>>([]);
  const [busy, setBusy] = useState<boolean>(false);
  const [summaryResults, setSummaryResults] = useState<string | null>("");
  const [summaryPrompt, setSummaryPrompt] = useState<string>();
  const [serviceType, setServiceType] = useState<ServiceTypes>("summary");
  const [settingsOpened, setSettingsOpened] = useState<boolean>(false);
  const question = useRef<string>();
  const chatData = useRef<Array<object>>([]);
  const socket = useRef<WebSocket>();
  const [connState, setConnState] = useState<string>("Disconnected");

  const messagesDP = useRef(
    new MutableArrayDataProvider<MessageToastItem["summary"], MessageToastItem>(
      [],
      { keyAttributes: "summary" }
    )
  );

  const gateway = `ws://${window.location.hostname}:1986`;
  let sockTimer: any = null;

  // setup the websocket connection
  const initWebSocket = () => {
    console.log("Trying to open a WebSocket connection...");
    socket.current = new WebSocket(gateway);
    socket.current.binaryType = "arraybuffer";
    socket.current.onopen = onOpen;
    socket.current.onerror = onError;
    socket.current.onclose = onClose;
    socket.current.onmessage = onMessage;
  };

  // handle all messages coming from the websocket service
  const onMessage = (event: any) => {
    const msg = JSON.parse(event.data);

    switch (msg.msgType) {
      // switch (Object.keys(msg)[0]) {
      case "message":
        console.log("message: ", msg.data);
        return msg.data;
      case "question":
        console.log("question: ", msg.data);
        return msg.data;
      case "summary":
        console.log("summary");
        setSummaryResults(msg.data);
        return;
      case "answer":
        console.log("answer: ", msg.data);
        if (msg.data !== "connected") {
          let tempArray = [...chatData.current];
          // remove the animation item before adding answer
          setBusy(false);
          tempArray.pop();
          messagesDP.current.data = [];
          tempArray.push({
            id: tempArray.length as number,
            answer: msg.data,
          });
          chatData.current = tempArray;
          setUpdate(chatData.current);
        }
        return msg.data;
      default:
        return "unknown";
    }
  };

  const onOpen = () => {
    clearInterval(sockTimer);
    console.log("Connection opened");
    socket.current?.send(
      JSON.stringify({ msgType: "message", data: "connected" })
    );
    setConnState("Connected");
  };

  // if the connection is lost, wait one minute and try again.
  const onError = () => {
    sockTimer = setInterval(initWebSocket, 1000 * 60);
  };
  function onClose() {
    console.log("Connection closed");
    setConnState("Disconnected");
    socket.current ? (socket.current.onclose = () => {}) : null;
    socket.current?.close();
  }

  // Simulation code
  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
  const runSimulation = async () => {
    let Q = true;
    let x: number = 0;
    let y: number = 0;
    let tempArray: Array<Chat> = [];
    for (let index = 0; index < 8; index++) {
      if (Q) {
        if (x > 0) tempArray.pop();
        tempArray.push({ question: JSON.parse(Questions)[x] });
        // tempArray.push({ loading: "loading" });
        Q = false;
        x++;
      } else {
        tempArray.push({ answer: JSON.parse(Answers)[y] });
        if (y < JSON.parse(Answers).length - 1)
          tempArray.push({ loading: "loading" });
        Q = true;
        y++;
      }
      setUpdate([...tempArray]);
      await sleep(2000);
    }
  };
  useEffect(() => {
    switch (serviceType) {
      case "text":
        initWebSocket();
        console.log("Running Gen AI");
        return;
      case "sim":
        runSimulation();
        console.log("running simulation");
        return;
      case "summary":
        initWebSocket();
        console.log("summary loading");
        return;
    }
    return () => {
      socket.current ? (socket.current.onclose = () => {}) : null;
      socket.current?.close();
    };
  }, [serviceType]);

  const handleQuestionChange = (
    event: InputSearchElement.ojValueAction<null, null>
  ) => {
    // if we are waiting for an answer to be returned, throw an alert and return
    if (busy) {
      messagesDP.current.data = [
        {
          summary: "Still waiting for an answer!",
          detail: "Hang in there a little longer.",
          autoTimeout: "on",
        },
      ];
      //alert("Still waiting for an answer!  Hang in there a little longer.");
      return;
    }
    if (event.detail.value) {
      question.current = event.detail.value;
      let tempArray = [...chatData.current];
      tempArray.push({
        id: tempArray.length as number,
        question: question.current,
      });
      chatData.current = tempArray;
      setUpdate(chatData.current);

      // adding loading animation while we wait for answer to come back
      let tempAnswerArray = [...chatData.current];
      tempAnswerArray.push({
        id: tempAnswerArray.length as number,
        loading: "loading",
      });
      chatData.current = tempAnswerArray;
      setUpdate(chatData.current);
      setBusy(true);

      // simulating the delay for now just to show what the animation looks like.
      setTimeout(() => {
        socket.current?.send(
          JSON.stringify({ msgType: "question", data: question.current })
        );
      }, 300);
    }
  };

  const handleFileUpload = (file: ArrayBuffer) => {
    socket.current?.send(file);
  };

  const handleDrawerState = () => {
    setSettingsOpened(false);
  };
  const toggleDrawer = () => {
    setSettingsOpened(!settingsOpened);
  };
  const handleToastClose = () => {
    messagesDP.current.data = [];
  };

  const serviceTypeChangeHandler = (service: ServiceTypes) => {
    setUpdate([]);
    chatData.current = [];
    setServiceType(service);
    toggleDrawer();
  };

  const clearSummary = () => {
    setSummaryResults("");
  };

  const updateSummaryPrompt = (val: string) => {
    setSummaryPrompt(val);
  };

  return (
    <div class="oj-web-applayout-max-width oj-web-applayout-content oj-flex oj-sm-flex-direction-column demo-bg-main">
      <oj-c-drawer-popup
        edge="end"
        opened={settingsOpened}
        onojBeforeClose={handleDrawerState}
        aria-label="Settings Drawer"
      >
        <Settings
          serviceType={serviceType}
          serviceChange={serviceTypeChangeHandler}
        />
      </oj-c-drawer-popup>
      <div class="oj-flex-bar oj-flex-item demo-header oj-sm-12">
        <oj-c-message-toast
          data={messagesDP.current}
          position="top"
          onojClose={handleToastClose}
        ></oj-c-message-toast>
        {/* <h1 class="oj-typography-heading-lg oj-flex-bar-start"> </h1> */}
        <div class="oj-flex-bar-end oj-color-invert demo-header-end">
          {/* <h6 class="oj-sm-margin-2x-end">{connState}</h6> */}
          <oj-button onojAction={toggleDrawer} label="Toggle" display="icons">
            <span slot="startIcon" class="oj-ux-ico-menu"></span>
          </oj-button>
        </div>
      </div>
      {serviceType === "text" && (
        <Chat
          data={update}
          question={question}
          questionChanged={handleQuestionChange}
        />
      )}
      {serviceType === "sim" && (
        <Simulation
          data={update}
          question={question}
          questionChanged={handleQuestionChange}
        />
      )}
      {serviceType === "summary" && (
        <Summary
          fileChanged={handleFileUpload}
          summary={summaryResults}
          clear={clearSummary}
          prompt={updateSummaryPrompt}
        />
      )}
    </div>
  );
};
export default Content;
