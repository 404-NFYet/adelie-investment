/**
 * useSlashCommands - / 명령어 처리 훅
 * 
 * /buy, /sell, /portfolio 등의 명령어를 감지하고 바로 실행
 */
import { useCallback, useMemo } from 'react';

const SLASH_COMMANDS = {
  '/buy': {
    id: 'buy_stock',
    label: '매수',
    description: '종목 매수 주문',
    requiresConfirmation: false,
    parseArgs: (args) => {
      const [stockCode, quantity] = args.split(/\s+/);
      return { stock_code: stockCode, quantity: parseInt(quantity) || 1 };
    },
  },
  '/sell': {
    id: 'sell_stock',
    label: '매도',
    description: '종목 매도 주문',
    requiresConfirmation: false,
    parseArgs: (args) => {
      const [stockCode, quantity] = args.split(/\s+/);
      return { stock_code: stockCode, quantity: parseInt(quantity) || 1 };
    },
  },
  '/portfolio': {
    id: 'check_portfolio',
    label: '포트폴리오',
    description: '내 포트폴리오 확인',
    requiresConfirmation: false,
    parseArgs: () => ({}),
  },
  '/briefing': {
    id: 'get_briefing',
    label: '브리핑',
    description: '오늘의 브리핑 보기',
    requiresConfirmation: false,
    parseArgs: () => ({}),
  },
  '/quiz': {
    id: 'start_quiz',
    label: '퀴즈',
    description: '퀴즈 시작',
    requiresConfirmation: false,
    parseArgs: () => ({}),
  },
  '/review': {
    id: 'create_review_card',
    label: '복습카드',
    description: '복습 카드 생성',
    requiresConfirmation: false,
    parseArgs: () => ({}),
  },
  '/dart': {
    id: 'fetch_dart',
    label: 'DART',
    description: 'DART 공시 조회',
    requiresConfirmation: false,
    parseArgs: (args) => ({ stock_code: args.trim() }),
  },
  '/price': {
    id: 'check_stock_price',
    label: '시세',
    description: '실시간 시세 확인',
    requiresConfirmation: false,
    parseArgs: (args) => ({ stock_code: args.trim() }),
  },
  '/help': {
    id: 'show_help',
    label: '도움말',
    description: '사용 가능한 명령어 보기',
    requiresConfirmation: false,
    parseArgs: () => ({}),
  },
};

export default function useSlashCommands({ onExecute, onMessage }) {
  const parseCommand = useCallback((input) => {
    const trimmed = (input || '').trim();
    if (!trimmed.startsWith('/')) return null;

    const parts = trimmed.split(/\s+/);
    const command = parts[0].toLowerCase();
    const argsString = parts.slice(1).join(' ');

    const commandDef = SLASH_COMMANDS[command];
    if (!commandDef) return null;

    return {
      command,
      commandDef,
      args: commandDef.parseArgs(argsString),
      raw: trimmed,
    };
  }, []);

  const executeCommand = useCallback(async (input) => {
    const parsed = parseCommand(input);
    if (!parsed) return { handled: false };

    const { command, commandDef, args } = parsed;

    if (command === '/help') {
      const helpText = Object.entries(SLASH_COMMANDS)
        .map(([cmd, def]) => `**${cmd}** - ${def.description}`)
        .join('\n');
      
      if (onMessage) {
        onMessage({
          role: 'assistant',
          content: `### 사용 가능한 명령어\n\n${helpText}`,
          isSlashCommand: true,
        });
      }
      return { handled: true, result: 'help_shown' };
    }

    if (onExecute) {
      try {
        const result = await onExecute({
          id: commandDef.id,
          type: 'slash_command',
          label: commandDef.label,
          params: args,
          requiresConfirmation: commandDef.requiresConfirmation,
        });
        return { handled: true, result };
      } catch (error) {
        console.error('Slash command execution failed:', error);
        return { handled: true, error };
      }
    }

    return { handled: true };
  }, [parseCommand, onExecute, onMessage]);

  const isSlashCommand = useCallback((input) => {
    return parseCommand(input) !== null;
  }, [parseCommand]);

  const getSuggestions = useCallback((input) => {
    const trimmed = (input || '').trim().toLowerCase();
    if (!trimmed.startsWith('/')) return [];

    return Object.entries(SLASH_COMMANDS)
      .filter(([cmd]) => cmd.startsWith(trimmed))
      .map(([cmd, def]) => ({
        command: cmd,
        label: def.label,
        description: def.description,
      }))
      .slice(0, 5);
  }, []);

  const commands = useMemo(() => SLASH_COMMANDS, []);

  return {
    parseCommand,
    executeCommand,
    isSlashCommand,
    getSuggestions,
    commands,
  };
}
