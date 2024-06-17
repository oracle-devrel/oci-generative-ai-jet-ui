import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Chat from "./Chat";
import Summary from "./Summary";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Chat />,
  },
  {
    path: "/summary",
    element: <Summary />,
  },
]);

function Routing() {
  return <RouterProvider router={router} />;
}

export default Routing;
