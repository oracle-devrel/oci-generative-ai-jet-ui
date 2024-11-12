import { Question } from "./question";
import { Answer } from "./answer";
import { Loading } from "./loading";
import { ComponentProps } from "preact";
import { useEffect, useRef, useState, MutableRef } from "preact/hooks";
import "ojs/ojlistview";
import { ojListView } from "ojs/ojlistview";
import MutableArrayDataProvider = require("ojs/ojmutablearraydataprovider");
import Context = require("ojs/ojcontext");

type Props = {
  testId?: string;
  data: any;
  questionChanged: (event: any) => void;
  question: MutableRef<string | undefined>;
};

type Item = {
  id: number;
  answer?: string;
  question?: string;
  loading?: string;
};

type ListProps = ComponentProps<"oj-list-view">;
const madp = new MutableArrayDataProvider<Item["id"], Item>([], {
  keyAttributes: "id",
});

export const Chat = ({ testId, data, questionChanged, question }: Props) => {
  const dataProvider = useRef(madp);
  const listRef = useRef<ojListView<Item["id"], Item>>(null);
  const [lastKey, setLastKey] = useState<number>(0);

  const scrollPos: ListProps["scrollPosition"] = { key: lastKey };
  let busyContext = Context.getContext(
    listRef.current as ojListView<Item["id"], Item>
  ).getBusyContext();

  useEffect(() => {
    dataProvider.current.data = data;
    console.log("lastKey before set: ", lastKey);

    // the use of BusyContext here should not be required. It's a workaround for JET-64237.
    // it can be removed once the bug is fixed.
    busyContext.whenReady().then(() => {
      setLastKey(data.length - 1);
    });
  }, [data, busyContext]);

  const chatNoDataTemplate = () => {
    return (
      <div class="oj-flex oj-sm-justify-content-center demo-no-data-layout">
        <div class="oj-typography-heading-md oj-text-color-primary">
          Be the first to ask a question!
        </div>
      </div>
    );
  };

  const chatItemTemplate = (item: ojListView.ItemTemplateContext) => {
    return (
      <>
        {item.data.answer && <Answer item={item} sim={false} />}
        {item.data.loading && <Loading />}
        {item.data.question && <Question item={item} sim={false} />}
      </>
    );
  };

  return (
    <>
      <div class="oj-flex-item oj-sm-12">
        <oj-list-view
          id="chatlist"
          ref={listRef}
          data-oj-context="true"
          aria-label="list of questions and answers"
          data={dataProvider.current}
          selectionMode="none"
          scrollPosition={scrollPos}
          class="oj-sm-width-full demo-chat-layout"
        >
          <template slot="itemTemplate" render={chatItemTemplate}></template>
          <template slot="noData" render={chatNoDataTemplate}></template>
        </oj-list-view>
      </div>
      <oj-input-search
        id="search1"
        class="oj-input-search-hero oj-sm-width-3"
        value={question?.current}
        placeholder="ask me anything..."
        aria-label="enter a question"
        onojValueAction={questionChanged}
      ></oj-input-search>
    </>
  );
};
