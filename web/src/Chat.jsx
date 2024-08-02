import { useState, useEffect, useContext } from "react";
import { Box, CircularProgress, Snackbar } from "@mui/material";
import PromptInput from "./PromptInput";
import Conversation from "./Conversation";
import { useStomp } from "./stompHook";
import IdentityContext from "./IdentityContext";

function Chat() {
  const identity = useContext(IdentityContext);
  const [conversation, setConversation] = useState([]);
  const [promptValue, setPromptValue] = useState("");
  const [waiting, setWaiting] = useState(false);
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState();
  const [modelId, setModelId] = useState();
  const [models, setModels] = useState();
  const [updateModels, setUpdateModels] = useState(true);
  const { subscribe, unsubscribe, send, isConnected } = useStomp();

  // useEffect(() => {
  //   const fecthModels = async () => {
  //     try {
  //       const response = await fetch("/api/genai/models");
  //       const data = await response.json();
  //       setModels(
  //         data.filter(
  //           ({ capabilities }) =>
  //             capabilities.length === 1 &&
  //             capabilities.includes("TEXT_GENERATION")
  //         )
  //       );
  //     } catch (error) {
  //       setErrorMessage("Error fetching Generative AI Models from Backend");
  //     }
  //   };

  //   if (updateModels) {
  //     setUpdateModels(false);
  //     fecthModels();
  //   }
  // }, [updateModels]);

  useEffect(() => {
    let timeoutId;
    if (waiting) {
      timeoutId = setTimeout(() => {
        setWaiting(false);
        setShowError(true);
        setErrorMessage("Request timeout");
      }, 30000);
    } else {
    }
    return () => (timeoutId ? clearTimeout(timeoutId) : null);
  }, [waiting]);

  useEffect(() => {
    if (isConnected) {
      subscribe("/user/queue/answer", (message) => {
        setWaiting(false);
        if (message.errorMessage.length > 0) {
          setErrorMessage(message.errorMessage);
          setShowError(true);
        } else {
          setConversation((c) => [
            ...c,
            {
              id: c.length + 1,
              user: "ai",
              content: message.content,
            },
          ]);
        }
      });
    }

    return () => {
      unsubscribe("/user/queue/answer");
    };
  }, [isConnected]);

  useEffect(() => {
    if (isConnected && promptValue.length) {
      send("/genai/prompt", {
        conversationId: identity,
        content: promptValue,
        modelId: "notapply",
      });
      setWaiting(true);
      setPromptValue("");
    }
    return () => {};
  }, [promptValue]);

  return (
    <Box>
      {/* <FormControl fullWidth>
        <InputLabel id="model-label">Model</InputLabel>
        <Select
          labelId="model-label"
          id="model"
          defaultValue={""}
          label="Models"
          onChange={(e) => setModelId(e.target.value)}
        >
          {models &&
            models.map((model) => (
              <MenuItem key={model.id} value={model.id}>
                {model.name} v{model.version} ({model.capabilities.join(", ")})
              </MenuItem>
            ))}
        </Select>
      </FormControl>
      <Divider style={{ margin: "1rem" }} /> */}
      <Conversation>{conversation}</Conversation>
      {waiting && <CircularProgress style={{ padding: "1rem" }} />}
      <PromptInput
        setConversation={setConversation}
        setPromptValue={setPromptValue}
        disabled={waiting}
      ></PromptInput>
      <Snackbar
        open={showError}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        autoHideDuration={6000}
        onClose={() => {
          setErrorMessage();
          setShowError(false);
        }}
        message={errorMessage}
      />
    </Box>
  );
}

export default Chat;
