import { Menu, useTranslate } from "react-admin";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import ReceiptIcon from "@mui/icons-material/Receipt";
import EmailIcon from "@mui/icons-material/Email";
import DescriptionIcon from "@mui/icons-material/Description";
import ChatIcon from "@mui/icons-material/Chat";
import VideoLibraryIcon from "@mui/icons-material/VideoLibrary";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import AttachEmailIcon from "@mui/icons-material/AttachEmail";
import SettingsInputComponentIcon from "@mui/icons-material/SettingsInputComponent";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import { Divider, Typography, Box } from "@mui/material";

export const AppMenu = () => {
  const translate = useTranslate();
  return (
    <Menu>
      <Menu.DashboardItem />
      <Menu.Item to="/runs" primaryText={translate("aiflow.resources.runs")} leftIcon={<PlayArrowIcon />} />
      <Menu.Item to="/documents" primaryText={translate("aiflow.resources.documents")} leftIcon={<ReceiptIcon />} />
      <Menu.Item to="/emails" primaryText={translate("aiflow.resources.emails")} leftIcon={<EmailIcon />} />
      <Menu.Item
        to="/costs"
        primaryText={translate("aiflow.costs.title")}
        leftIcon={<AttachMoneyIcon />}
      />

      <Box sx={{ px: 2, pt: 2, pb: 0.5 }}>
        <Divider />
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
          {translate("aiflow.menu.skillViewers")}
        </Typography>
      </Box>

      <Menu.Item
        to="/process-docs"
        primaryText={translate("aiflow.skills.process_documentation")}
        leftIcon={<DescriptionIcon />}
      />
      <Menu.Item
        to="/rag-chat"
        primaryText={translate("aiflow.skills.aszf_rag_chat")}
        leftIcon={<ChatIcon />}
      />
      <Menu.Item
        to="/cubix"
        primaryText={translate("aiflow.skills.cubix_course_capture")}
        leftIcon={<VideoLibraryIcon />}
      />
      <Menu.Item
        to="/document-upload"
        primaryText={translate("aiflow.documentUpload.menuLabel")}
        leftIcon={<UploadFileIcon />}
      />
      <Menu.Item
        to="/email-upload"
        primaryText={translate("aiflow.emailUpload.menuLabel")}
        leftIcon={<AttachEmailIcon />}
      />
      <Menu.Item
        to="/email-connectors"
        primaryText={translate("aiflow.connectors.menuLabel")}
        leftIcon={<SettingsInputComponentIcon />}
      />
    </Menu>
  );
};
