import "preact";
import "oj-c/progress-bar";

export const Loading = () => {
  return (
    <li class="oj-flex demo-answer-layout">
      <div class="oj-flex-item oj-flex-bar">
        <div class="oj-sm-justify-content-center oj-flex-bar-middle oj-sm-padding-2x">
          {/* <div class="oj-sm-justify-content-center oj-flex-bar-middle oj-sm-padding-2x oj-color-invert"> */}
          <div class="oj-sm-4 oj-sm-padding-1x-top oj-color-invert">
            <oj-c-progress-bar
              value={-1}
              aria-label="loading answer"
            ></oj-c-progress-bar>
          </div>
        </div>
      </div>
    </li>
  );
};
