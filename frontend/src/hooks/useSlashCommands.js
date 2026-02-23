/**
 * useSlashCommands - / 명령어 처리 훅
 * 
 * /buy, /sell, /매수, /매도 등의 명령어를 감지하고 바로 실행
 */
import { useCallback, useMemo } from 'react';

const SLASH_COMMANDS = {
  '/buy': {
    id: 'buy_stock',
    label: '매수',
    description: '종목 매수 주문',
    requiresConfirmation: true,
    parseArgs: (args) => {
      const parts = args.trim().split(/\s+/);
      return { 
        stock_code: parts[0] || '', 
        quantity: parseInt(parts[1]) || 1,
        raw_args: args.trim(),
      };
    },
  },
  '/매수': {
    id: 'buy_stock',
    label: '매수',
    description: '종목 매수 주문',
    requiresConfirmation: true,
    parseArgs: (args) => {
      const cleaned = args.trim()
        .replace(/주\s*(사줘|매수|구매|살게|사고\s*싶어)?/gi, '')
        .replace(/(사줘|매수해줘|구매해줘|살게요?)/gi, '')
        .trim();
      const parts = cleaned.split(/\s+/).filter(Boolean);
      const quantityMatch = args.match(/(\d+)\s*주/);
      return { 
        stock_code: parts[0] || '', 
        quantity: quantityMatch ? parseInt(quantityMatch[1]) : (parseInt(parts[1]) || 1),
        raw_args: args.trim(),
      };
    },
  },
  '/sell': {
    id: 'sell_stock',
    label: '매도',
    description: '종목 매도 주문',
    requiresConfirmation: true,
    parseArgs: (args) => {
      const parts = args.trim().split(/\s+/);
      return { 
        stock_code: parts[0] || '', 
        quantity: parseInt(parts[1]) || 1,
        raw_args: args.trim(),
      };
    },
  },
  '/매도': {
    id: 'sell_stock',
    label: '매도',
    description: '종목 매도 주문',
    requiresConfirmation: true,
    parseArgs: (args) => {
      const cleaned = args.trim()
        .replace(/주\s*(팔아줘|매도|판매|팔게|팔고\s*싶어)?/gi, '')
        .replace(/(팔아줘|매도해줘|판매해줘|팔게요?)/gi, '')
        .trim();
      const parts = cleaned.split(/\s+/).filter(Boolean);
      const quantityMatch = args.match(/(\d+)\s*주/);
      return { 
        stock_code: parts[0] || '', 
        quantity: quantityMatch ? parseInt(quantityMatch[1]) : (parseInt(parts[1]) || 1),
        raw_args: args.trim(),
      };
    },
  },
  '/portfolio': {
    id: 'check_portfolio',
    label: '포트폴리오',
    description: '내 포트폴리오 확인',
    requiresConfirmation: false,
    parseArgs: () => ({}),
  },
  '/포트폴리오': {
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
  '/브리핑': {
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
  '/퀴즈': {
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
  '/복습': {
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
  '/공시': {
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
  '/시세': {
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
  '/도움말': {
    id: 'show_help',
    label: '도움말',
    description: '사용 가능한 명령어 보기',
    requiresConfirmation: false,
    parseArgs: () => ({}),
  },
  '/chart': {
    id: 'visualize',
    label: '차트',
    description: '데이터 시각화 (차트 생성)',
    requiresConfirmation: false,
    parseArgs: (args) => ({ topic: args.trim() }),
  },
  '/시각화': {
    id: 'visualize',
    label: '시각화',
    description: '데이터 시각화 (차트 생성)',
    requiresConfirmation: false,
    parseArgs: (args) => ({ topic: args.trim() }),
  },
  '/차트': {
    id: 'visualize',
    label: '차트',
    description: '데이터 시각화 (차트 생성)',
    requiresConfirmation: false,
    parseArgs: (args) => ({ topic: args.trim() }),
  },
  '/비교': {
    id: 'compare',
    label: '비교',
    description: '종목 비교 분석',
    requiresConfirmation: false,
    parseArgs: (args) => ({ stocks: args.trim() }),
  },
};

const UNIQUE_COMMANDS = [
  { command: '/매수', label: '매수', description: '종목 매수 주문' },
  { command: '/매도', label: '매도', description: '종목 매도 주문' },
  { command: '/포트폴리오', label: '포트폴리오', description: '내 포트폴리오 확인' },
  { command: '/브리핑', label: '브리핑', description: '오늘의 브리핑 보기' },
  { command: '/시각화', label: '시각화', description: '데이터 차트 생성' },
  { command: '/시세', label: '시세', description: '실시간 시세 확인' },
  { command: '/비교', label: '비교', description: '종목 비교 분석' },
  { command: '/공시', label: 'DART', description: 'DART 공시 조회' },
  { command: '/퀴즈', label: '퀴즈', description: '퀴즈 시작' },
  { command: '/복습', label: '복습카드', description: '복습 카드 생성' },
  { command: '/도움말', label: '도움말', description: '사용 가능한 명령어 보기' },
];

export default function useSlashCommands({ onExecute, onMessage }) {
  const parseCommand = useCallback((input) => {
    const trimmed = (input || '').trim();
    if (!trimmed.startsWith('/')) return null;

    const spaceIndex = trimmed.indexOf(' ');
    const command = spaceIndex > 0 ? trimmed.slice(0, spaceIndex) : trimmed;
    const argsString = spaceIndex > 0 ? trimmed.slice(spaceIndex + 1) : '';

    const commandDef = SLASH_COMMANDS[command] || SLASH_COMMANDS[command.toLowerCase()];
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

    if (commandDef.id === 'show_help') {
      const helpText = UNIQUE_COMMANDS
        .map((c) => `**${c.command}** - ${c.description}`)
        .join('\n');
      
      if (onMessage) {
        onMessage({
          role: 'assistant',
          content: `### 사용 가능한 명령어\n\n${helpText}\n\n예시: \`/매수 삼성전자 10\`, \`/시세 005930\``,
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
          command,
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
    const trimmed = (input || '').trim();
    if (!trimmed.startsWith('/')) return [];

    if (trimmed === '/') {
      return UNIQUE_COMMANDS.slice(0, 6);
    }

    return UNIQUE_COMMANDS
      .filter((c) => c.command.startsWith(trimmed) || c.label.includes(trimmed.slice(1)))
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
