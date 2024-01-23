import { Header } from "./header";
import Content from "./content/index";
import { registerCustomElement } from "ojs/ojvcomponent";
import "preact";

type Props = {
  appName: string;
};

export const App = registerCustomElement("app-root", (props: Props) => {
  props.appName = "Generative AI JET UI";

  return (
    <div id="appContainer" class="oj-web-applayout-page">
      <Header appName={props.appName} />
      <Content />
    </div>
  );
});
