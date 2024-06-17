import { Container, Typography } from "@mui/material";
import { StompProvider } from "./stompHook";
import Chat from "./Chat";
import Routing from "./Routing";

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
      <Container>
        <Typography variant="h2" component="h2">
          OCI GenAI PoC
        </Typography>
        <Routing />
      </Container>
    </StompProvider>
  );
}

export default App;
