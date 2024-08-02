import { Container, Typography } from "@mui/material";
import { StompProvider } from "./stompHook";
import Routing from "./Routing";
import { v4 as uuidv4 } from "uuid";
import IdentityContext from "./IdentityContext";

let conversationId;
if (localStorage.getItem("conversationId")) {
  conversationId = localStorage.getItem("conversationId");
} else {
  conversationId = uuidv4();
  localStorage.setItem("conversationId", conversationId);
}

const protocol = window.location.protocol === "http:" ? "ws://" : "wss://";
const hostname =
  window.location.hostname === "localhost"
    ? "localhost:8080"
    : window.location.hostname;
const brokerURL = `${protocol}${hostname}/websocket`;

function App() {
  return (
    <StompProvider
      config={{
        brokerURL: brokerURL,
      }}
    >
      <IdentityContext.Provider value={conversationId}>
        <Container>
          <Typography variant="h2" component="h2">
            OCI GenAI PoC
          </Typography>
          <Routing />
        </Container>
      </IdentityContext.Provider>
    </StompProvider>
  );
}

export default App;
