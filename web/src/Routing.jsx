import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Chat from "./Chat";
import Summary from "./Summary";
import SummaryText from "./SummaryText";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Chat />,
  },
  {
    path: "/summary",
    element: <Summary />,
  },
  {
    path: "/summaryText",
    element: <SummaryText />,
  },
]);

function Routing() {
  return <RouterProvider router={router} />;
}

export default Routing;
