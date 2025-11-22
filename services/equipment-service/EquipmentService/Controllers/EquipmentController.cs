using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using EquipmentService.Models;
using EquipmentService.Data;

namespace EquipmentService.Controllers
{
    /// <summary>
    /// API controller for managing equipment with PostgreSQL database
    /// </summary>
    [ApiController]
    [Route("api/equipment")]
    public class EquipmentController : ControllerBase
    {
        private readonly EquipmentDbContext _context;
        private readonly ILogger<EquipmentController> _logger;

        // Constructor - Dependency Injection provides DbContext
        public EquipmentController(EquipmentDbContext context, ILogger<EquipmentController> logger)
        {
            _context = context;
            _logger = logger;
        }

        /// <summary>
        /// GET /api/equipment - Get all equipment
        /// </summary>
        [HttpGet]
        public async Task<ActionResult<IEnumerable<Equipment>>> GetAll()
        {
            var equipment = await _context.Equipment.ToListAsync();
            return Ok(equipment);
        }

        /// <summary>
        /// GET /api/equipment/{id} - Get equipment by ID
        /// </summary>
        [HttpGet("{id}")]
        public async Task<ActionResult<Equipment>> GetById(int id)
        {
            var equipment = await _context.Equipment.FindAsync(id);
            
            if (equipment == null)
                return NotFound(new { message = $"Equipment with ID {id} not found" });
            
            return Ok(equipment);
        }

        /// <summary>
        /// POST /api/equipment - Create new equipment
        /// </summary>
        [HttpPost]
        public async Task<ActionResult<Equipment>> Create(Equipment equipment)
        {
            equipment.CreatedAt = DateTime.UtcNow;
            
            _context.Equipment.Add(equipment);
            await _context.SaveChangesAsync();
            
            _logger.LogInformation("Created new equipment: {TagNumber}", equipment.TagNumber);
            
            return CreatedAtAction(nameof(GetById), new { id = equipment.Id }, equipment);
        }

        /// <summary>
        /// PUT /api/equipment/{id} - Update existing equipment
        /// </summary>
        [HttpPut("{id}")]
        public async Task<ActionResult> Update(int id, Equipment equipment)
        {
            if (id != equipment.Id)
                return BadRequest(new { message = "ID mismatch" });

            var existing = await _context.Equipment.FindAsync(id);
            
            if (existing == null)
                return NotFound(new { message = $"Equipment with ID {id} not found" });

            // Update fields
            existing.TagNumber = equipment.TagNumber;
            existing.Name = equipment.Name;
            existing.Type = equipment.Type;
            existing.Status = equipment.Status;
            existing.Capacity = equipment.Capacity;
            existing.Unit = equipment.Unit;
            existing.InstallDate = equipment.InstallDate;
            existing.UpdatedAt = DateTime.UtcNow;

            await _context.SaveChangesAsync();
            
            _logger.LogInformation("Updated equipment: {TagNumber}", equipment.TagNumber);

            return Ok(existing);
        }

        /// <summary>
        /// DELETE /api/equipment/{id} - Delete equipment
        /// </summary>
        [HttpDelete("{id}")]
        public async Task<ActionResult> Delete(int id)
        {
            var equipment = await _context.Equipment.FindAsync(id);
            
            if (equipment == null)
                return NotFound(new { message = $"Equipment with ID {id} not found" });

            _context.Equipment.Remove(equipment);
            await _context.SaveChangesAsync();
            
            _logger.LogInformation("Deleted equipment: {TagNumber}", equipment.TagNumber);
            
            return NoContent();
        }

        /// <summary>
        /// GET /api/equipment/stats - Get equipment statistics
        /// </summary>
        [HttpGet("stats")]
        public async Task<ActionResult<object>> GetStats()
        {
            var stats = new
            {
                totalCount = await _context.Equipment.CountAsync(),
                operatingCount = await _context.Equipment.CountAsync(e => e.Status == "Operating"),
                maintenanceCount = await _context.Equipment.CountAsync(e => e.Status == "Maintenance"),
                equipmentTypes = await _context.Equipment
                    .GroupBy(e => e.Type)
                    .Select(g => new { type = g.Key, count = g.Count() })
                    .ToListAsync()
            };
            
            return Ok(stats);
        }

        /// <summary>
        /// GET /api/equipment/search?query=... - Search equipment
        /// </summary>
        [HttpGet("search")]
        public async Task<ActionResult<IEnumerable<Equipment>>> Search([FromQuery] string query)
        {
            if (string.IsNullOrWhiteSpace(query))
                return BadRequest(new { message = "Search query is required" });

            var equipment = await _context.Equipment
                .Where(e => e.TagNumber.Contains(query) || e.Name.Contains(query))
                .ToListAsync();

            return Ok(equipment);
        }
    }
}
