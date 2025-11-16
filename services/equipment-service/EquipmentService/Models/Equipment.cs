namespace EquipmentService.Models
{
    /// <summary>
    /// Represents a piece of industrial equipment in the refinery
    /// </summary>
    public class Equipment
    {
        /// <summary>
        /// Unique identifier for the equipment
        /// </summary>
        public int Id { get; set; }

        /// <summary>
        /// Equipment tag number (e.g., P-101, E-201)
        /// </summary>
        public string TagNumber { get; set; } = string.Empty;

        /// <summary>
        /// Descriptive name of the equipment
        /// </summary>
        public string Name { get; set; } = string.Empty;

        /// <summary>
        /// Type of equipment (e.g., Pump, Heat Exchanger, Reactor)
        /// </summary>
        public string Type { get; set; } = string.Empty;

        /// <summary>
        /// Current operational status
        /// </summary>
        public string Status { get; set; } = "Operating";

        /// <summary>
        /// Design capacity (flow rate, power, volume, etc.)
        /// </summary>
        public double? Capacity { get; set; }

        /// <summary>
        /// Unit of measurement for capacity (m³/h, MW, kg/s, etc.)
        /// </summary>
        public string? Unit { get; set; }

        /// <summary>
        /// Installation or commissioning date
        /// </summary>
        public DateTime InstallDate { get; set; }

        /// <summary>
        /// When this record was created
        /// </summary>
        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        /// <summary>
        /// When this record was last updated
        /// </summary>
        public DateTime? UpdatedAt { get; set; }
    }
}
