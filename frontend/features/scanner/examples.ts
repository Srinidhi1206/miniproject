import type { Channel } from "@/types/api";

// Fictional example messages so people can see how SENTINEL works without
// pasting their own. Clearly labelled as examples in the UI.
export const EXAMPLES: { label: string; channel: Channel; text: string }[] = [
  {
    label: "Example: bank KYC SMS",
    channel: "sms",
    text: "Dear customer, your SBI YONO account will be blocked today due to pending KYC. Update PAN immediately at http://sbi-kyc-verify.co/update to avoid suspension.",
  },
  {
    label: "Example: part-time job offer",
    channel: "whatsapp",
    text: "Hello, I am Priya from HR. We are hiring for online work, 30 min per day, salary Rs 8000/day by liking YouTube videos. Pay Rs 499 registration fee to start. Join our Telegram group t.me/earn-daily-task",
  },
  {
    label: "Example: marketplace buyer",
    channel: "whatsapp",
    text: "Hi, I am buying your sofa listed on OLX. I am in army, I will pay by QR code. Just scan the QR I send and enter your UPI PIN to receive 15000.",
  },
  {
    label: "Example: genuine bank OTP",
    channel: "sms",
    text: "482913 is your OTP for login to HDFC Bank NetBanking. It is valid for 5 minutes. Do not share this OTP with anyone. HDFC Bank never asks for OTP.",
  },
  {
    label: "Example: message from a friend",
    channel: "whatsapp",
    text: "Hey, are we still meeting at 7 near the cafe? Let me know if you're running late.",
  },
];
