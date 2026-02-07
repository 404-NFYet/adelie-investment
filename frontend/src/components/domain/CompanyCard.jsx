/**
 * CompanyCard.jsx - 회사 카드
 * 회사 정보와 역할 배지를 표시
 */
const ROLE_STYLES = {
  leader: { label: '대장주', className: 'badge-primary' },
  equipment: { label: '장비주', className: 'badge-info' },
  potential: { label: '잠룡', className: 'badge-success' },
  competitor: { label: '경쟁사', className: 'badge-warning' },
};

export default function CompanyCard({ 
  name, 
  code, 
  role = 'leader', 
  description, 
  changeRate,
  onClick 
}) {
  const roleStyle = ROLE_STYLES[role] || ROLE_STYLES.leader;
  const isPositive = changeRate > 0;

  return (
    <div onClick={onClick} className="card card-interactive cursor-pointer">
      <div className="flex items-start justify-between mb-3">
        {/* Company Info */}
        <div className="flex items-center gap-3">
          {/* Company Initial */}
          <div className="w-12 h-12 rounded-full bg-primary-light flex items-center justify-center">
            <span className="text-xl font-bold text-primary">
              {name?.charAt(0)}
            </span>
          </div>
          <div>
            <h3 className="font-bold">{name}</h3>
            <span className="text-sm text-secondary">{code}</span>
          </div>
        </div>
        
        {/* Role Badge */}
        <span className={`badge ${roleStyle.className}`}>
          {roleStyle.label}
        </span>
      </div>
      
      {/* Description */}
      {description && (
        <p className="text-sm text-secondary mb-3">{description}</p>
      )}
      
      {/* Change Rate */}
      {changeRate !== undefined && (
        <div className={`text-sm font-semibold ${isPositive ? 'text-gain' : 'text-loss'}`}>
          {isPositive ? '+' : ''}{changeRate}%
        </div>
      )}
    </div>
  );
}
