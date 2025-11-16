using Microsoft.EntityFrameworkCore;
using EquipmentService.Models;

namespace EquipmentService.Data
{
    /// <summary>
    /// Database context for Equipment Service
    /// This is the "bridge" between your C# code and PostgreSQL database
    /// </summary>
    public class EquipmentDbContext : DbContext
    {
        // CONSTRUCTOR
        // Receives configuration (connection string, etc.) and passes to parent DbContext
        public EquipmentDbContext(DbContextOptions<EquipmentDbContext> options)
            : base(options)
        {
        }

        // TABLE DEFINITION
        // This creates a table called "Equipment" in the database
        // DbSet<Equipment> = "A set of Equipment records in the database"
        public DbSet<Equipment> Equipment { get; set; }

        // CONFIGURATION METHOD
        // This method runs when EF Core is creating the database model
        // Here we specify exactly how we want the database structured
        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            // CONFIGURE EQUIPMENT TABLE
            modelBuilder.Entity<Equipment>(entity =>
            {
                // 1. TABLE NAME
                entity.ToTable("Equipment");

                // 2. PRIMARY KEY
                // Id is the unique identifier for each equipment
                entity.HasKey(e => e.Id);

                // 3. REQUIRED FIELDS WITH MAX LENGTH
                // TagNumber: Required, max 50 chars (e.g., "P-101", "E-201")
                entity.Property(e => e.TagNumber)
                    .IsRequired()
                    .HasMaxLength(50);

                // Name: Required, max 200 chars (e.g., "Crude Feed Pump")
                entity.Property(e => e.Name)
                    .IsRequired()
                    .HasMaxLength(200);

                // Type: Required, max 100 chars (e.g., "Centrifugal Pump")
                entity.Property(e => e.Type)
                    .IsRequired()
                    .HasMaxLength(100);

                // Status: Required, max 50 chars, defaults to "Operating"
                entity.Property(e => e.Status)
                    .IsRequired()
                    .HasMaxLength(50)
                    .HasDefaultValue("Operating");

                // Unit: Optional (nullable), max 50 chars (e.g., "m³/h", "MW")
                entity.Property(e => e.Unit)
                    .HasMaxLength(50);

                // 4. INDEXES (for faster searches)
                
                // Unique index on TagNumber
                // Why? No two equipment can have same tag number
                // Benefit: Fast lookup by tag, prevents duplicates
                entity.HasIndex(e => e.TagNumber)
                    .IsUnique();

                // Regular index on Type
                // Why? Often search by equipment type
                // Benefit: Fast queries like "Show all pumps"
                entity.HasIndex(e => e.Type);

                // Regular index on Status
                // Why? Often filter by status (Operating, Maintenance, etc.)
                // Benefit: Fast queries like "Show all operating equipment"
                entity.HasIndex(e => e.Status);
            });

            // 5. SEED DATA (Initial sample data)
            // FIXED: Using DateTime.SpecifyKind to mark as UTC
            // PostgreSQL requires timezone info for timestamp columns
            modelBuilder.Entity<Equipment>().HasData(
                new Equipment
                {
                    Id = 1,
                    TagNumber = "P-101",
                    Name = "Crude Feed Pump",
                    Type = "Centrifugal Pump",
                    Status = "Operating",
                    Capacity = 500,
                    Unit = "m³/h",
                    // FIXED: Specify UTC timezone
                    InstallDate = DateTime.SpecifyKind(new DateTime(2020, 1, 15), DateTimeKind.Utc),
                    CreatedAt = DateTime.SpecifyKind(DateTime.UtcNow, DateTimeKind.Utc)
                },
                new Equipment
                {
                    Id = 2,
                    TagNumber = "E-201",
                    Name = "Crude Preheat Exchanger",
                    Type = "Shell & Tube Heat Exchanger",
                    Status = "Operating",
                    Capacity = 50,
                    Unit = "MW",
                    // FIXED: Specify UTC timezone
                    InstallDate = DateTime.SpecifyKind(new DateTime(2019, 6, 20), DateTimeKind.Utc),
                    CreatedAt = DateTime.SpecifyKind(DateTime.UtcNow, DateTimeKind.Utc)
                },
                new Equipment
                {
                    Id = 3,
                    TagNumber = "T-301",
                    Name = "Distillation Column",
                    Type = "Fractionation Tower",
                    Status = "Operating",
                    Capacity = 100000,
                    Unit = "bbl/day",
                    // FIXED: Specify UTC timezone
                    InstallDate = DateTime.SpecifyKind(new DateTime(2018, 3, 10), DateTimeKind.Utc),
                    CreatedAt = DateTime.SpecifyKind(DateTime.UtcNow, DateTimeKind.Utc)
                }
            );
        }
    }
}
