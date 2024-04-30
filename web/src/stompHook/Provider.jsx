import React, { createContext, useEffect, useState } from "react";
import { Client } from "@stomp/stompjs";

const defaultValue = {
  isConnected: false,
  stompClient: null,
  subscriptions: {},
  setSubscriptions: () => {},
};

export const StompContext = createContext(defaultValue);

export const StompProvider = ({ children, config, onConnected }) => {
  const [stompClient, setStompClient] = useState(new Client(config));
  const [subscriptions, setSubscriptions] = useState({});

  useEffect(() => {
    stompClient?.activate();
    onConnected?.(stompClient);
    return () => {
      stompClient?.deactivate();
    };
  }, [stompClient]);

  return (
    <StompContext.Provider
      value={{
        stompClient,
        subscriptions,
        setSubscriptions,
      }}
    >
      {children}
    </StompContext.Provider>
  );
};
