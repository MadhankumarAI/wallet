import { Platform } from "react-native";

const getBaseUrl = () => {
  // 🔥 YOUR ACTUAL NGROK URL
  const ngrokUrl = "https://a7e639eb2fba.ngrok-free.app";
  
  // Use ngrok URL for all platforms since local network isn't accessible
  return ngrokUrl;
};

export const API_URL = getBaseUrl();

// 🔧 Debug: Log the API URL
console.log("API_URL in tunnel mode:", getBaseUrl());
console.log("Platform:", Platform.OS);