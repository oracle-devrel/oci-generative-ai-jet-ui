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
  const protocol = window.location.protocol === "http:" ? "ws://" : "wss://";
  const hostname =
    window.location.hostname === "localhost"
      ? "localhost:8080"
      : window.location.hostname;
  const serviceURL = `${protocol}${hostname}/websocket`;
  let snippets: Array<string> = [];
  let codesnipIdx = 0;

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

  const getIdxs = (searchTxt: string, data: string) => {
    let idx = 0;
    let tempArray = [];
    while (idx !== -1) {
      idx = data.indexOf(searchTxt, idx + 1);
      tempArray.push(idx);
    }
    return tempArray;
  };

  const getCodeSnippets = (indexes: Array<number>, data: string) => {
    let i = 0;
    snippets = [];
    while (i < indexes.length - 1 && indexes[0] !== -1) {
      let tempStr = data.substring(indexes[i], indexes[i + 1]);
      let langLen = tempStr.indexOf("\n");
      let trimmed = tempStr.substring(langLen);
      snippets.push(trimmed);
      i += 2;
    }
    console.log("snippets: ", snippets);
    console.log("codesnipIdx in getCodeSnippets: ", codesnipIdx);
    return snippets;
  };

  const addButtons = () => {
    setTimeout(() => {
      const codeSections: HTMLCollectionOf<HTMLPreElement> =
        document.getElementsByTagName("pre");
      let x = 0;
      for (let i = codesnipIdx; i < Array.from(codeSections).length; i++) {
        let tempStr = JSON.stringify(snippets[x]);
        let btn = document.createElement("button");
        btn.setAttribute("id", "btn-" + codesnipIdx);
        btn.setAttribute("onclick", "copytoclip(" + tempStr + ")");
        // btn.setAttribute("class", "copy-to-clip-btn");
        btn.innerText = "Copy";
        btn.style.cssText = `position:relative;float:right`;
        codeSections[codesnipIdx]?.prepend(btn);
        console.log("codesnipIdx before increment in addButton: ", codesnipIdx);
        codesnipIdx++;
        x++;
      }
    }, 750);
  };
  const getClipboardOptions = (data: string) => {
    const searchTxt = "```";
    const indexes = getIdxs(searchTxt, data);
    const snippets = getCodeSnippets(indexes, data);
    return indexes[0] != -1 ? true : false;
  };

  const onMessage = (msg: any) => {
    let aiAnswer = JSON.parse(msg.body).content;
    if (msg.data !== "connected") {
      let tempArray = [...chatData.current];
      // remove the animation item before adding answer
      setBusy(false);
      tempArray.pop();
      messagesDP.current.data = [];
      const snipsExist = getClipboardOptions(aiAnswer);
      tempArray.push({
        id: tempArray.length as number,
        answer: aiAnswer,
      });
      chatData.current = tempArray;
      setUpdate(chatData.current);
      snipsExist ? addButtons() : null;
    }
  };
  return client;
};

export const sendPrompt = (
  client: Client | null,
  prompt: string,
  modelId: string,
  convoId: string,
  finetune: boolean
) => {
  if (client?.connected) {
    console.log("Sending prompt: ", prompt);
    client.publish({
      destination: "/genai/prompt",
      body: JSON.stringify({
        conversationId: convoId,
        content: prompt,
        modelId: modelId,
        finetune: finetune,
      }),
    });
  } else {
    console.log("Error, no Stomp connection");
  }
};
