using Microsoft.AspNetCore.Mvc;
using EquipmentService.Models;

namespace EquipmentService.Controllers
{
    /// <summary>
    /// API controller for managing equipment
    /// </summary>
    [ApiController]
    [Route("api/[controller]")]
    public class EquipmentController : ControllerBase
    {
        // In-memory storage (temporary - will use database later)
        private static List<Equipment> _equipment = new()
        {
            new Equipment 
            { 
                Id = 1, 
                TagNumber = "P-101", 
                Name = "Crude Feed Pump",
                Type = "Centrifugal Pump",
                Status = "Operating",
                Capacity = 500,
                Unit = "m³/h",
                InstallDate = new DateTime(2020, 1, 15)
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
                InstallDate = new DateTime(2019, 6, 20)
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
                InstallDate = new DateTime(2018, 3, 10)
            }
        };

        /// <summary>
        /// Get all equipment
        /// </summary>
        [HttpGet]
        public ActionResult<IEnumerable<Equipment>> GetAll()
        {
            return Ok(_equipment);
        }

        /// <summary>
        /// Get equipment by ID
        /// </summary>
        [HttpGet("{id}")]
        public ActionResult<Equipment> GetById(int id)
        {
            var equipment = _equipment.FirstOrDefault(e => e.Id == id);
            
            if (equipment == null)
                return NotFound(new { message = $"Equipment with ID {id} not found" });
            
            return Ok(equipment);
        }

        /// <summary>
        /// Create new equipment
        /// </summary>
        [HttpPost]
        public ActionResult<Equipment> Create(Equipment equipment)
        {
            // Generate new ID
            equipment.Id = _equipment.Any() ? _equipment.Max(e => e.Id) + 1 : 1;
            equipment.CreatedAt = DateTime.UtcNow;
            
            _equipment.Add(equipment);
            
            return CreatedAtAction(
                nameof(GetById), 
                new { id = equipment.Id }, 
                equipment
            );
        }

        /// <summary>
        /// Update existing equipment
        /// </summary>
        [HttpPut("{id}")]
        public ActionResult Update(int id, Equipment equipment)
        {
            var existing = _equipment.FirstOrDefault(e => e.Id == id);
            
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

            return Ok(existing);
        }

        /// <summary>
        /// Delete equipment
        /// </summary>
        [HttpDelete("{id}")]
        public ActionResult Delete(int id)
        {
            var equipment = _equipment.FirstOrDefault(e => e.Id == id);
            
            if (equipment == null)
                return NotFound(new { message = $"Equipment with ID {id} not found" });

            _equipment.Remove(equipment);
            
            return NoContent();
        }

        /// <summary>
        /// Get equipment statistics
        /// </summary>
        [HttpGet("stats")]
        public ActionResult<object> GetStats()
        {
            var stats = new
            {
                totalCount = _equipment.Count,
                operatingCount = _equipment.Count(e => e.Status == "Operating"),
                maintenanceCount = _equipment.Count(e => e.Status == "Maintenance"),
                equipmentTypes = _equipment.GroupBy(e => e.Type)
                    .Select(g => new { type = g.Key, count = g.Count() })
                    .ToList()
            };
            
            return Ok(stats);
        }
    }
}
