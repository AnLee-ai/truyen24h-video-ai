import type { ChatActionSource, ChatRequestedIntent } from "./types";

const READ_ONLY_TOOLS = new Set(["read", "grep", "ls"]);

export function shouldRefreshSidebarForTool(toolName: string): boolean {
  return !READ_ONLY_TOOLS.has(toolName);
}

// 与服务端 server.ts 的确认式生产任务路由保持一致：
// 这些 intent 走服务端的确认式生产分支（task-store 跟踪、可长时间运行）。
// 这样的发送轮不是"聊天轮"——请求会挂起到任务结束，
// 期间用户应当仍能继续聊天，所以它不置 isChatStreaming。
const CONFIRMED_PRODUCTION_INTENTS: ReadonlySet<ChatRequestedIntent> = new Set([
  "create_book",
  "write_next",
  "short_run",
  "script_create",
  "storyboard_create",
  "interactive_film_create",
  "translation_create",
  "play_start",
  "generate_cover",
  "draft_structure",
  "connect_choice",
  "remove_node",
] as const);

export function isConfirmedProductionSend(
  actionSource: ChatActionSource,
  requestedIntent: ChatRequestedIntent | undefined,
): boolean {
  if (requestedIntent === undefined || !CONFIRMED_PRODUCTION_INTENTS.has(requestedIntent)) {
    return false;
  }
  // 写下一章由书籍会话的快捷按钮触发（actionSource=quick-action），
  // 服务端同样把它作为后台生产任务执行。
  if (requestedIntent === "write_next") {
    return actionSource === "button" || actionSource === "slash" || actionSource === "quick-action";
  }
  return actionSource === "button" || actionSource === "slash";
}
