import "preact";

const gateway = `ws://${window.location.hostname}:1986`;
let sockTimer: any = null;

export const initWebSocket = (
  setSummaryResults: any,
  setBusy: any,
  setUpdate: any,
  messagesDP: any,
  socket: any,
  chatData: any
) => {
  // const [connState, setConnState] = useState<string>("Disconnected");
  console.log("Trying to open a WebSocket connection...");
  socket.current = new WebSocket(gateway);
  socket.current.binaryType = "arraybuffer";

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
        console.log("summary: ", msg.data);
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
    //setConnState("Connected");
  };

  // if the connection is lost, wait one minute and try again.
  const onError = () => {
    //sockTimer = setInterval(initWebSocket, 1000 * 60);
  };
  function onClose() {
    console.log("Connection closed");
    //setConnState("Disconnected");
    socket.current ? (socket.current.onclose = () => {}) : null;
    socket.current?.close();
  }

  socket.current.onopen = onOpen;
  socket.current.onerror = onError;
  socket.current.onclose = onClose;
  socket.current.onmessage = onMessage;
};
