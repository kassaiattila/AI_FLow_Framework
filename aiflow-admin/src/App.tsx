import { Admin, Resource, CustomRoutes } from "react-admin";
import { Route } from "react-router-dom";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import ReceiptIcon from "@mui/icons-material/Receipt";
import EmailIcon from "@mui/icons-material/Email";
import { Layout } from "./Layout";
import { Dashboard } from "./Dashboard";
import { authProvider } from "./authProvider";
import { dataProvider } from "./dataProvider";
import { i18nProvider } from "./i18nProvider";
import { lightTheme, darkTheme } from "./theme";
import { RunList } from "./resources/RunList";
import { RunShow } from "./resources/RunShow";
import { InvoiceList } from "./resources/InvoiceList";
import { InvoiceShow } from "./resources/InvoiceShow";
import { EmailList } from "./resources/EmailList";
import { EmailShow } from "./resources/EmailShow";
import { ProcessDocViewer } from "./pages/ProcessDocViewer";
import { RagChat } from "./pages/RagChat";
import { CubixViewer } from "./pages/CubixViewer";
import { InvoiceUpload } from "./pages/InvoiceUpload";
import { EmailUpload } from "./pages/EmailUpload";
import { CostsPage } from "./pages/CostsPage";
import { VerificationPanel } from "./verification/VerificationPanel";

export const App = () => (
  <Admin
    layout={Layout}
    dashboard={Dashboard}
    authProvider={authProvider}
    dataProvider={dataProvider}
    i18nProvider={i18nProvider}
    theme={lightTheme}
    darkTheme={darkTheme}
    defaultTheme="dark"
  >
    <Resource
      name="runs"
      list={RunList}
      show={RunShow}
      icon={PlayArrowIcon}
      options={{ label: "Workflow Runs" }}
    />
    <Resource
      name="invoices"
      list={InvoiceList}
      show={InvoiceShow}
      icon={ReceiptIcon}
      options={{ label: "Invoices" }}
    />
    <Resource
      name="emails"
      list={EmailList}
      show={EmailShow}
      icon={EmailIcon}
      options={{ label: "Emails" }}
    />
    <CustomRoutes>
      <Route path="/process-docs" element={<ProcessDocViewer />} />
      <Route path="/rag-chat" element={<RagChat />} />
      <Route path="/cubix" element={<CubixViewer />} />
      <Route path="/invoice-upload" element={<InvoiceUpload />} />
      <Route path="/email-upload" element={<EmailUpload />} />
      <Route path="/costs" element={<CostsPage />} />
      <Route path="/invoices/:id/verify" element={<VerificationPanel />} />
    </CustomRoutes>
  </Admin>
);
