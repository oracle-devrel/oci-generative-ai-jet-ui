import { Header } from "./header";
import Content from "./content/index";
import { registerCustomElement } from "ojs/ojvcomponent";
import { createContext } from "preact";

type Props = {
  appName: string;
};
const convoUUID = window.crypto.randomUUID();
export const ConvoCtx = createContext(convoUUID);

export const App = registerCustomElement("app-root", (props: Props) => {
  props.appName = "Generative AI JET UI";

  return (
    <div id="appContainer" class="oj-web-applayout-page">
      <ConvoCtx.Provider value={convoUUID}>
        {console.log("UUID: ", convoUUID)}
        <Header appName={props.appName} />
        <Content />
      </ConvoCtx.Provider>
    </div>
  );
});
