import { Admin, Resource } from "react-admin";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { Layout } from "./Layout";
import { Dashboard } from "./Dashboard";
import { authProvider } from "./authProvider";
import { dataProvider } from "./dataProvider";
import { i18nProvider } from "./i18nProvider";
import { RunList } from "./resources/RunList";
import { RunShow } from "./resources/RunShow";

export const App = () => (
  <Admin
    layout={Layout}
    dashboard={Dashboard}
    authProvider={authProvider}
    dataProvider={dataProvider}
    i18nProvider={i18nProvider}
    darkTheme={{ palette: { mode: "dark" } }}
  >
    <Resource
      name="runs"
      list={RunList}
      show={RunShow}
      icon={PlayArrowIcon}
      options={{ label: "Workflow Runs" }}
    />
  </Admin>
);
