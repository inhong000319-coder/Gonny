import React from "react";
import ReactDOM from "react-dom/client";
import { AppRouterProvider } from "./app/providers/router-provider";
import { QueryAppProvider } from "./app/providers/query-provider";
import { AuthProvider } from "./app/providers/auth-provider";
import "./app/styles/tokens.css";
import "./app/styles/globals.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryAppProvider>
      <AuthProvider>
        <AppRouterProvider />
      </AuthProvider>
    </QueryAppProvider>
  </React.StrictMode>,
);
