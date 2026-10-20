import { format } from "./format";

export function App(props: { name: string }) {
  return <div className="app">{format(props.name)}</div>;
}
