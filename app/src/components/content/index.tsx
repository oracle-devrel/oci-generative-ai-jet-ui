import Chat from "./chat";
import "preact";
import "ojs/ojinputsearch";
import "oj-c/message-toast";
import MutableArrayDataProvider = require("ojs/ojmutablearraydataprovider");
import { MessageToastItem } from "oj-c/message-toast";
import { InputSearchElement } from "ojs/ojinputsearch";
import { useState, useEffect, useRef } from "preact/hooks";

const Content = () => {
  const [update, setUpdate] = useState<Array<object>>([]);
  const [busy, setBusy] = useState<boolean>(false);
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
    socket.current.onopen = onOpen;
    socket.current.onerror = onError;
    socket.current.onclose = onClose;
    socket.current.onmessage = onMessage;
  };

  // handle all messages coming from the websocket service
  const onMessage = (event: any) => {
    const msg = JSON.parse(event.data);

    switch (Object.keys(msg)[0]) {
      case "message":
        console.log("message: ", msg.message);
        return msg.message;
      case "question":
        console.log("question: ", msg.question);
        return msg.question;
      case "answer":
        console.log("answer: ", msg.answer);
        if (msg.answer !== "connected") {
          let tempArray = [...chatData.current];
          // remove the animation item before adding answer
          setBusy(false);
          tempArray.pop();
          messagesDP.current.data = [];
          tempArray.push({
            id: tempArray.length as number,
            answer: msg.answer,
          });
          chatData.current = tempArray;
          setUpdate(chatData.current);
        }
        return msg.answer;
      default:
        return "unknown";
    }
  };

  const onOpen = () => {
    clearInterval(sockTimer);
    console.log("Connection opened");
    socket.current?.send(JSON.stringify({ message: "connected" }));
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

  useEffect(() => {
    initWebSocket();
    return () => {
      socket.current ? (socket.current.onclose = () => {}) : null;
      socket.current?.close();
    };
  }, []);

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
        socket.current?.send(JSON.stringify({ question: question.current }));
      }, 300);
    }
  };

  const handleToastClose = () => {
    messagesDP.current.data = [];
  };

  return (
    <div class="oj-web-applayout-max-width oj-web-applayout-content oj-flex oj-sm-flex-direction-column demo-bg-main">
      {/* <div class="oj-flex-bar oj-flex-item demo-header">
        <oj-c-message-toast
          data={messagesDP.current}
          position="top"
          onojClose={handleToastClose}
        ></oj-c-message-toast>
        <h1 class="oj-typography-heading-lg oj-flex-bar-start"> </h1>
        <div class="oj-flex-bar-end oj-color-invert demo-header-end">
          <h6 class="oj-sm-margin-2x-end">{connState}</h6>
        </div>
      </div> */}
      <div class="oj-flex-item">
        <Chat data={update} />
      </div>
      <oj-input-search
        id="search1"
        class="oj-input-search-hero oj-sm-width-3"
        value={question.current}
        placeholder="ask me anything..."
        aria-label="enter a question"
        onojValueAction={handleQuestionChange}
      ></oj-input-search>
    </div>
  );
};
export default Content;
