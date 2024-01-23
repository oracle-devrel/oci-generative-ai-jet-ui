import "preact";
import { ojListView } from "ojs/ojlistview";
import "ojs/ojavatar";

type Props = {
  item: ojListView.ItemTemplateContext;
};
export const Question = ({ item }: Props) => {
  return (
    <li class="oj-flex demo-question-layout">
      <div class="oj-flex-item oj-flex-bar">
        <div class="oj-flex-bar-start">
          <oj-avatar
            initials="Q"
            size="sm"
            role="presentation"
            background="orange"
          ></oj-avatar>
        </div>
        <div class="oj-sm-justify-content-flex-start oj-flex-bar-middle oj-sm-padding-2x demo-copy-paste oj-color-invert">
          {item.data.question}
        </div>
      </div>
    </li>
  );
};
