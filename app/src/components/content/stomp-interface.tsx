import "preact";
import { Client } from "stompjs";

// setup the Stompjs connection
export const InitStomp = (
  setBusy: any,
  setUpdate: any,
  messagesDP: any,
  chatData: any,
  serviceType: any
) => {
  //const [test, setTest] = useState();
  const protocol = window.location.protocol === "http:" ? "ws://" : "wss://";
  const hostname =
    window.location.hostname === "localhost"
      ? "localhost:8080"
      : window.location.hostname;
  const serviceURL = `${protocol}${hostname}/websocket`;
  console.log("in the stomp init module");
  const client = new Client({
    brokerURL: serviceURL,
    onConnect: () => {
      if (serviceType === "text") {
        client.subscribe("/user/queue/answer", (message: any) => {
          console.log("Answer message: ", JSON.parse(message.body).content);
          onMessage(message);
        });
      } else if (serviceType === "summary") {
        client.subscribe("/user/queue/summary", (message: any) => {
          console.log("Summary message: ", JSON.parse(message.body).content);
          onMessage(message);
        });
      }
    },
    onStompError: (e) => {
      console.log("Stomp Error: ", e);
    },
    onWebSocketError: () => {
      console.log("Error connecting to Websocket service");
      serviceType === "text"
        ? client.unsubscribe("/user/queue/answer")
        : client.unsubscribe("/user/queue/summary");
      client.deactivate();
    },
  });
  client.activate();

  const onMessage = (msg: any) => {
    let aiAnswer = JSON.parse(msg.body).content;
    //console.log("answer: ", aiAnswer);
    if (msg.data !== "connected") {
      let tempArray = [...chatData.current];
      // remove the animation item before adding answer
      setBusy(false);
      tempArray.pop();
      messagesDP.current.data = [];
      tempArray.push({
        id: tempArray.length as number,
        answer: aiAnswer,
      });
      chatData.current = tempArray;
      setUpdate(chatData.current);
    }
  };
  return client;
};

export const sendPrompt = (client: Client | null, prompt: string) => {
  if (client?.connected) {
    console.log("Sending prompt: ", prompt);
    client.publish({
      destination: "/genai/prompt",
      body: JSON.stringify({
        conversationId: "something",
        content: prompt, //"Show me code for a websocket service using JavaScript",
        modelId: "notapply",
      }),
    });
  } else {
    console.log("Error, no Stomp connection");
  }
};
