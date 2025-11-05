import { marketData, Asset, Transaction, Order, Position, ChartDataPoint, OrderBook, Contact, RiskMetrics } from '../types';

export const mockmarketData: marketData = {
  totalBalance: 125429.87,
  totalPnL: 8542.33,
  totalPnLPercentage: 7.31,
  usdsBalance: 15420.50,
  dayChange: 1247.89,
  dayChangePercentage: 1.01,
};

export const mockAssets: Asset[] = [
  {
    id: 'BTC',
    symbol: 'BTC',
    name: 'Bitcoin',
    price: 67450.32,
    change24h: 1205.78,
    change24hPercentage: 1.82,
    marketCap: 1324567890000,
    volume24h: 28965432100,
    holdings: 0.85472,
    value: 57642.15,
  },
  {
    id: 'ETH',
    symbol: 'ETH',
    name: 'Ethereum',
    price: 3842.67,
    change24h: -156.23,
    change24hPercentage: -3.91,
    marketCap: 462345678900,
    volume24h: 15678901234,
    holdings: 12.45,
    value: 47833.95,
  },
  {
    id: 'AAPL',
    symbol: 'AAPL',
    name: 'Apple Inc.',
    price: 178.25,
    change24h: 2.45,
    change24hPercentage: 1.39,
    marketCap: 2789012345678,
    volume24h: 98765432100,
    holdings: 50,
    value: 8912.50,
  },
  {
    id: 'TSLA',
    symbol: 'TSLA',
    name: 'Tesla Inc.',
    price: 245.80,
    change24h: -8.92,
    change24hPercentage: -3.50,
    marketCap: 781234567890,
    volume24h: 45678901234,
    holdings: 25,
    value: 6145.00,
  },
];

export const mockTransactions: Transaction[] = [
  {
    id: '1',
    type: 'buy',
    asset: 'BTC',
    amount: 0.15,
    price: 66890.45,
    total: 10033.57,
    timestamp: new Date('2024-01-15T14:30:00Z'),
    status: 'completed',
  },
  {
    id: '2',
    type: 'sell',
    asset: 'ETH',
    amount: 2.5,
    price: 3920.15,
    total: 9800.38,
    timestamp: new Date('2024-01-15T12:15:00Z'),
    status: 'completed',
  },
  {
    id: '3',
    type: 'transfer',
    asset: 'USDS',
    amount: 5000,
    price: 1.00,
    total: 5000,
    timestamp: new Date('2024-01-15T09:45:00Z'),
    status: 'completed',
  },
  {
    id: '4',
    type: 'swap',
    asset: 'AAPL',
    amount: 10,
    price: 176.80,
    total: 1768.00,
    timestamp: new Date('2024-01-14T16:20:00Z'),
    status: 'pending',
  },
];

export const mockOrders: Order[] = [
  {
    id: '1',
    type: 'buy',
    orderType: 'limit',
    asset: 'BTC',
    amount: 0.25,
    price: 66500.00,
    total: 16625.00,
    filled: 0,
    status: 'open',
    timestamp: new Date('2024-01-15T15:30:00Z'),
  },
  {
    id: '2',
    type: 'sell',
    orderType: 'stop',
    asset: 'ETH',
    amount: 1.5,
    price: 3700.00,
    total: 5550.00,
    filled: 0,
    status: 'open',
    timestamp: new Date('2024-01-15T14:45:00Z'),
  },
];

export const mockPositions: Position[] = [
  {
    id: '1',
    asset: 'BTC/USD',
    side: 'long',
    size: 0.5,
    entryPrice: 45000,
    markPrice: 47000,
    pnl: 1000,
    pnlPercentage: 4.44,
    margin: 4500,
    leverage: 5,
    timestamp: new Date('2025-01-15T10:00:00Z'), // ➕ ADD THIS
  },
  {
    id: '2',
    asset: 'ETH/USD',
    side: 'short',
    size: 10,
    entryPrice: 2500,
    markPrice: 2450,
    pnl: 500,
    pnlPercentage: 2.0,
    margin: 5000,
    leverage: 5,
    timestamp: new Date('2025-01-15T12:00:00Z'), // ➕ ADD THIS
  },
];

export const generateMockChartData = (days: number = 30): ChartDataPoint[] => {
  const data: ChartDataPoint[] = [];
  let price = 65000;
  const now = new Date();
  
  for (let i = days - 1; i >= 0; i--) {
    const timestamp = new Date(now.getTime() - i * 24 * 60 * 60 * 1000).getTime();
    const change = (Math.random() - 0.5) * 2000;
    const open = price;
    price += change;
    const high = Math.max(open, price) + Math.random() * 500;
    const low = Math.min(open, price) - Math.random() * 500;
    const close = price;
    const volume = Math.random() * 1000000000;
    
    data.push({
      timestamp,
      open,
      high,
      low,
      close,
      volume,
    });
  }
  
  return data;
};

export const mockOrderBook: OrderBook = {
  bids: [
    { price: 67449.32, size: 0.25, total: 16862.33 },
    { price: 67445.15, size: 0.18, total: 12140.13 },
    { price: 67441.90, size: 0.42, total: 28325.60 },
    { price: 67438.75, size: 0.15, total: 10115.81 },
    { price: 67435.20, size: 0.33, total: 22253.62 },
  ],
  asks: [
    { price: 67450.32, size: 0.28, total: 18886.09 },
    { price: 67454.78, size: 0.19, total: 12816.41 },
    { price: 67458.95, size: 0.35, total: 23610.63 },
    { price: 67462.40, size: 0.22, total: 14841.73 },
    { price: 67466.85, size: 0.41, total: 27661.41 },
  ],
};

export const mockContacts: Contact[] = [
  {
    id: '1',
    name: 'Alice Johnson',
    address: '0x742d35cc6635c0532925a3b8d86b7a582b7fbb1e',
    lastUsed: new Date('2024-01-14T10:30:00Z'),
  },
  {
    id: '2',
    name: 'Bob Smith',
    address: '0x8ba1f109551bd432803012645hac136c0a3f5ce1',
    lastUsed: new Date('2024-01-13T16:45:00Z'),
  },
  {
    id: '3',
    name: 'Carol Wilson',
    address: '0x2546bcd3c84621e976d8185a91a922ae77ecec30',
    lastUsed: new Date('2024-01-12T09:15:00Z'),
  },
];

export const mockRiskMetrics: RiskMetrics = {
  var: -2847.32,
  sharpeRatio: 1.47,
  maxDrawdown: -8.32,
  volatility: 24.67,
  beta: 1.23,
};