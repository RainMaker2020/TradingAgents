import { render, screen } from '@testing-library/react'
import ChiefAnalystCard from '@/features/run-detail/components/ChiefAnalystCard'
import type { ChiefAnalystReport } from '@/lib/types/agents'
import type { AgentStep } from '@/lib/types/run'

// react-to-pdf uses browser APIs not available in Jest — mock it
jest.mock('react-to-pdf', () => ({
  usePDF: () => ({ toPDF: jest.fn(), targetRef: { current: null } }),
}))

const mockReport: ChiefAnalystReport = {
  verdict:   'BUY',
  catalyst:  'Strong Q4 earnings beat with record margins',
  execution: 'Enter at market price, stop loss at $180',
  tail_risk: 'Federal Reserve rate hike could compress multiples',
}

const mockReports: Partial<Record<AgentStep, string[]>> = {
  market_analyst: ['Momentum improving'],
  research_manager: ['Synthesis indicates asymmetry to upside'],
  chief_analyst: [JSON.stringify(mockReport)],
}

test('shows pending state when status is pending and report is null', () => {
  render(<ChiefAnalystCard report={null} status="pending" ticker="AAPL" date="2024-01-15" reports={{}} />)
  expect(screen.getByText(/standing by/i)).toBeInTheDocument()
})

test('shows running skeleton when status is running', () => {
  render(<ChiefAnalystCard report={null} status="running" ticker="AAPL" date="2024-01-15" reports={{}} />)
  expect(screen.getByTestId('chief-analyst-card')).toBeInTheDocument()
})

test('shows verdict when status is done and report is provided', () => {
  render(<ChiefAnalystCard report={mockReport} status="done" ticker="AAPL" date="2024-01-15" reports={mockReports} />)
  expect(screen.getByText('BUY')).toBeInTheDocument()
})

test('shows institutional sections when done', () => {
  render(<ChiefAnalystCard report={mockReport} status="done" ticker="AAPL" date="2024-01-15" reports={mockReports} />)
  expect(screen.getByText(/time horizon/i)).toBeInTheDocument()
  expect(screen.getByText(/scenario matrix/i)).toBeInTheDocument()
  expect(screen.getByText(/sources summary/i)).toBeInTheDocument()
})

test('shows execution when done', () => {
  render(<ChiefAnalystCard report={mockReport} status="done" ticker="AAPL" date="2024-01-15" reports={mockReports} />)
  expect(screen.getAllByText(/Enter at market price/i).length).toBeGreaterThan(0)
})

test('shows tail_risk when done', () => {
  render(<ChiefAnalystCard report={mockReport} status="done" ticker="AAPL" date="2024-01-15" reports={mockReports} />)
  expect(screen.getAllByText(/Federal Reserve rate hike/i).length).toBeGreaterThan(0)
})

test('shows download button when done', () => {
  render(<ChiefAnalystCard report={mockReport} status="done" ticker="AAPL" date="2024-01-15" reports={mockReports} />)
  expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument()
})

test('shows report-unavailable fallback when done but report is null', () => {
  render(<ChiefAnalystCard report={null} status="done" ticker="AAPL" date="2024-01-15" reports={{}} />)
  expect(screen.getByText(/report unavailable/i)).toBeInTheDocument()
})

test('shows insufficient evidence markers when no upstream reports exist', () => {
  render(<ChiefAnalystCard report={mockReport} status="done" ticker="AAPL" date="2024-01-15" reports={{ chief_analyst: [JSON.stringify(mockReport)] }} />)
  expect(screen.getAllByText(/insufficient evidence/i).length).toBeGreaterThan(0)
})
