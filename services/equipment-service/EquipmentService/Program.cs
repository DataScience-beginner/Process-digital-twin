var builder = WebApplication.CreateBuilder(args);

// Add services to the container
builder.Services.AddControllers();  // ← THIS WAS MISSING!
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new Microsoft.OpenApi.Models.OpenApiInfo
    {
        Title = "Equipment Service API",
        Version = "v1",
        Description = "Digital Twin Equipment Management API"
    });
});

var app = builder.Build();

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

app.MapControllers();  // ← THIS WAS MISSING!

app.Run();
