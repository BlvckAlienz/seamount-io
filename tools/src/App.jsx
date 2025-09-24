import React from 'react'
import SavingsCalculator from './components/SavingsCalculator'

function App() {
  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '20px'
    }}>
      <SavingsCalculator />
    </div>
  )
}

export default App