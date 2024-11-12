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
  sim: boolean;
};

export const Answer = ({ item, sim }: Props) => {
  const answer = item.data.answer;
  return (
    <>
      {sim && (
        <li class="oj-flex demo-sim-answer-layout oj-bg-danger-30">
          <div class="oj-flex-item oj-flex-bar">
            <div class="oj-sm-justify-content-flex-end oj-flex-bar-middle oj-sm-padding-2x demo-copy-paste">
              <md-wrapper
                id="TestingOne"
                class="oj-sm-width-full"
                markdown={answer}
              />
            </div>
            <div class="oj-flex-bar-end">
              <oj-avatar
                size="sm"
                role="presentation"
                src="styles/images/placeholder-female-02.png"
                background="orange"
              ></oj-avatar>
            </div>
          </div>
        </li>
      )}
      {!sim && (
        <li class="oj-flex demo-answer-layout">
          <div class="oj-flex-item">
            <div class="oj-sm-justify-content-flex-end oj-sm-padding-2x-end oj-sm-12 demo-copy-paste oj-color-invert">
              <md-wrapper
                id="TestingOne"
                class="oj-sm-12"
                markdown={answer}
              />
            </div>
            {/* <div class="oj-flex-bar-end">
              <oj-avatar
                initials="A"
                size="sm"
                role="presentation"
                background="orange"
              ></oj-avatar>
            </div> */}
          </div>
        </li>
      )}
    </>
  );
};
