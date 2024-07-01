import "preact";
import { Client } from "stompjs";

// setup the Stompjs connection
export const InitStomp = (
  setBusy: any,
  setUpdate: any,
  messagesDP: any,
  chatData: any
) => {
  //const [test, setTest] = useState();
  const client = new Client({
    brokerURL: "ws://localhost:8080/websocket",
    onConnect: () => {
      client.subscribe("/user/queue/answer", (message: any) => {
        console.log("Answer message: ", JSON.parse(message.body).content);
        onMessage(message);
      });
    },
    onStompError: (e) => {
      console.log("Stomp Error: ", e);
    },
    onWebSocketError: () => {
      console.log("Error connecting to Websocket service");
      client.deactivate();
    },
  });
  client.activate();

  const onMessage = (msg: any) => {
    let aiAnswer = JSON.parse(msg.body).content;
    // console.log("answer: ", aiAnswer);
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
