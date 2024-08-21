import { Header } from "./header";
import Content from "./content/index";
import { registerCustomElement } from "ojs/ojvcomponent";
import { createContext } from "preact";

type Props = {
  appName: string;
};
const tempArray = new Uint32Array(10);
const convoUUID = window.crypto.getRandomValues(tempArray);

export const ConvoCtx = createContext("");

export const App = registerCustomElement("app-root", (props: Props) => {
  props.appName = "Generative AI JET UI";

  return (
    <div id="appContainer" class="oj-web-applayout-page">
      <ConvoCtx.Provider value={convoUUID[0].toString()}>
        {console.log("UUID: ", convoUUID[0].toString())}
        <Header appName={props.appName} />
        <Content />
      </ConvoCtx.Provider>
    </div>
  );
});
