import "preact";
import { useRef, useState, useEffect } from "preact/hooks";
import * as ResponsiveUtils from "ojs/ojresponsiveutils";
import "ojs/ojbutton";

type Props = Readonly<{
  appName: string;
}>;

export const Header = (props: Props) => {
  const mediaQueryRef = useRef<MediaQueryList>(
    window.matchMedia(ResponsiveUtils.getFrameworkQuery("sm-only")!)
  );

  const [isSmallWidth, setIsSmallWidth] = useState(
    mediaQueryRef.current.matches
  );

  useEffect(() => {
    mediaQueryRef.current.addEventListener("change", handleMediaQueryChange);
    return () =>
      mediaQueryRef.current.removeEventListener(
        "change",
        handleMediaQueryChange
      );
  }, [mediaQueryRef]);

  const handleMediaQueryChange = (e: MediaQueryListEvent) => {
    setIsSmallWidth(e.matches);
  };

  return (
    <header role="banner" class="oj-web-applayout-header">
      <div class="oj-web-applayout-max-width oj-flex-bar oj-sm-align-items-center">
        <div class="oj-flex-bar-middle oj-sm-align-items-baseline">
          <span
            role="img"
            class="oj-icon demo-oracle-icon"
            title="Oracle Logo"
            alt="Oracle Logo"></span>
          <h1 class="oj-web-applayout-header-title oj-color-invert">
            {props.appName}
          </h1>
        </div>
        <div class="oj-flex-bar-end"></div>
      </div>
    </header>
  );
};
