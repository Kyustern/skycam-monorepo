import { useMemo } from 'react'

// Toulouse visibility data based on average daily humidity ranges
const TOULOUSE_VISIBILITY_DATA = {
  January: { humidity_percent: [83, 87], visibility_km: [8, 12] },
  February: { humidity_percent: [79, 85], visibility_km: [10, 15] },
  March: { humidity_percent: [75, 81], visibility_km: [12, 18] },
  April: { humidity_percent: [68, 74], visibility_km: [18, 25] },
  May: { humidity_percent: [70, 76], visibility_km: [15, 22] },
  June: { humidity_percent: [67, 73], visibility_km: [20, 28] },
  July: { humidity_percent: [60, 71], visibility_km: [25, 40] },
  August: { humidity_percent: [65, 71], visibility_km: [22, 35] },
  September: { humidity_percent: [67, 73], visibility_km: [20, 28] },
  October: { humidity_percent: [75, 81], visibility_km: [12, 18] },
  November: { humidity_percent: [80, 86], visibility_km: [9, 14] },
  December: { humidity_percent: [83, 88], visibility_km: [8, 12] },
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
]

export const HumidityVisibilityDisplay = () => {
  const currentMonth = useMemo(() => {
    const date = new Date()
    return MONTH_NAMES[date.getMonth()]
  }, [])

  const monthData = useMemo(() => {
    return TOULOUSE_VISIBILITY_DATA[currentMonth as keyof typeof TOULOUSE_VISIBILITY_DATA]
  }, [currentMonth])

  if (!monthData) return null

  return (
    <div className="bg-black/70 text-white p-2 rounded text-xs font-mono">
      <div>
        <span className="text-gray-300">{currentMonth}</span>
      </div>
      <div>
        <span className="text-orange-400">Humidity: </span>
        <span className="text-orange-400">
          {monthData.humidity_percent[0]}–{monthData.humidity_percent[1]}%
        </span>
      </div>
      <div>
        <span className="text-green-400">Visibility: </span>
        <span className="text-green-400">
          {monthData.visibility_km[0]}–{monthData.visibility_km[1]} km
        </span>
      </div>
    </div>
  )
}
