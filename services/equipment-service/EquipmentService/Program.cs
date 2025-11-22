using Microsoft.EntityFrameworkCore;
using EquipmentService.Data;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container
builder.Services.AddControllers();

// ⭐ NEW: Add Database Context with PostgreSQL
builder.Services.AddDbContext<EquipmentDbContext>(options =>
{
    var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
    options.UseNpgsql(connectionString);
});

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new Microsoft.OpenApi.Models.OpenApiInfo
    {
        Title = "Equipment Service API",
        Version = "v1",
        Description = "Digital Twin Equipment Management API with PostgreSQL"
    });
});

var app = builder.Build();

// ⭐ NEW: Auto-migrate database on startup (for development)
using (var scope = app.Services.CreateScope())
{
    var dbContext = scope.ServiceProvider.GetRequiredService<EquipmentDbContext>();
    try
    {
        dbContext.Database.Migrate();
        app.Logger.LogInformation("Database migration completed successfully");
    }
    catch (Exception ex)
    {
        app.Logger.LogError(ex, "An error occurred while migrating the database");
    }
}

// Configure the HTTP request pipeline
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(options =>
    {
        options.SwaggerEndpoint("/swagger/v1/swagger.json", "Equipment Service v1");
    });
}

app.UseHttpsRedirection();

app.MapControllers();

app.Run();
