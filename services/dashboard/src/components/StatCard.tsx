export default function StatCard({ title, value, icon: Icon, trend, colorClass = "text-primary bg-primary-glow" }: { title: string, value: string | number, icon: any, trend?: { value: string, isUp: boolean }, colorClass?: string }) {
  return (
    <div className="bg-bg-surface border border-border-color rounded-xl p-6 glow-hover relative overflow-hidden">
      <div className={`absolute -right-4 -top-4 w-24 h-24 rounded-full filter blur-2xl opacity-20 ${colorClass.split(' ')[0].replace('text-', 'bg-')}`}></div>
      
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-text-secondary font-medium">{title}</h3>
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorClass}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      
      <div className="flex items-end justify-between mt-2">
        <p className="text-3xl font-bold text-text-primary">{value}</p>
        {trend && (
          <p className={`text-sm font-semibold flex items-center ${trend.isUp ? 'text-accent' : 'text-danger'}`}>
            {trend.isUp ? '↑' : '↓'} {trend.value}
          </p>
        )}
      </div>
    </div>
  );
}
