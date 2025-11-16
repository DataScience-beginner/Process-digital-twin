using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace EquipmentService.Data
{
    /// <summary>
    /// Factory for creating DbContext at design-time (during migrations)
    /// This tells 'dotnet ef' how to create a DbContext instance
    /// </summary>
    public class DesignTimeDbContextFactory : IDesignTimeDbContextFactory<EquipmentDbContext>
    {
        public EquipmentDbContext CreateDbContext(string[] args)
        {
            // Create options builder
            var optionsBuilder = new DbContextOptionsBuilder<EquipmentDbContext>();
            
            // Configure for PostgreSQL with a temporary connection string
            // This is ONLY used during migrations, not at runtime
            optionsBuilder.UseNpgsql(
                "Host=localhost;Port=5432;Database=equipmentdb;Username=equipmentuser;Password=equipment123"
            );
            
            // Return configured DbContext
            return new EquipmentDbContext(optionsBuilder.Options);
        }
    }
}
