export interface Message {
  text: string;
  author: string;
  tag: string;
}

export function messages(tag?: string | null): Message[];
export function randomMessage(tag?: string | null): Message;
export function formatMessage(msg: Message): string;
