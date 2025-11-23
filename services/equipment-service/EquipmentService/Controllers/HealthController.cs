using Microsoft.AspNetCore.Mvc;

namespace EquipmentService.Controllers;

[ApiController]
[Route("[controller]")]
public class HealthController : ControllerBase
{
    private readonly ILogger<HealthController> _logger;

    public HealthController(ILogger<HealthController> logger)
    {
        _logger = logger;
    }

    [HttpGet]
    public IActionResult Get()
    {
        // Simple health check - returns 200 OK if API is running
        return Ok(new
        {
            status = "Healthy",
            timestamp = DateTime.UtcNow,
            service = "Equipment API"
        });
    }
}
