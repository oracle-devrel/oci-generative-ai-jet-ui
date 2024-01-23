import "preact";
import "md-wrapper/loader";
import { ojListView } from "ojs/ojlistview";
import "ojs/ojavatar";

declare global {
  namespace preact.JSX {
    interface IntrinsicElements {
      "md-wrapper": any;
    }
  }
}

type Props = {
  item: ojListView.ItemTemplateContext;
};

export const Answer = ({ item }: Props) => {
  const answer = item.data.answer;
  return (
    <li class="oj-flex demo-answer-layout">
      <div class="oj-flex-item oj-flex-bar">
        <div class="oj-sm-justify-content-flex-end oj-flex-bar-middle oj-sm-padding-2x demo-copy-paste oj-color-invert">
          <md-wrapper
            id="TestingOne"
            class="oj-sm-width-full"
            markdown={`### Answer \n ${answer} `}
          />
        </div>

        <div class="oj-flex-bar-end">
          <oj-avatar
            initials="A"
            size="sm"
            role="presentation"
            background="orange"
          ></oj-avatar>
        </div>
      </div>
    </li>
  );
};
