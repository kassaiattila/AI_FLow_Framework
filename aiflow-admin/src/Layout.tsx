import type { ReactNode } from "react";
import { Layout as RALayout, CheckForApplicationUpdate } from "react-admin";
import { AppMenu } from "./Menu";
import { AIFlowAppBar } from "./AppBar";

export const Layout = ({ children }: { children: ReactNode }) => (
  <RALayout menu={AppMenu} appBar={AIFlowAppBar}>
    {children}
    <CheckForApplicationUpdate />
  </RALayout>
);
