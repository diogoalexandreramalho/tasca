/** A thin band of blue tiles, as on the customer website (where it's taller). */
export function AzulejoStrip({ height = 10 }: { height?: number }) {
  const id = `azulejo-${height}`;
  const c = height / 2;
  return (
    <svg aria-hidden className="block w-full" style={{ height }}>
      <defs>
        <pattern id={id} width={height} height={height} patternUnits="userSpaceOnUse">
          <rect width={height} height={height} fill="#e6f1fb" />
          <path
            d={`M${c} 1 L${height - 1} ${c} L${c} ${height - 1} L1 ${c} Z`}
            fill="none"
            stroke="#185fa5"
            strokeWidth="0.8"
          />
          <circle cx={c} cy={c} r={height / 8} fill="#185fa5" />
        </pattern>
      </defs>
      <rect width="100%" height={height} fill={`url(#${id})`} />
    </svg>
  );
}
