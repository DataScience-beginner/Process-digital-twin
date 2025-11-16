using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace EquipmentService.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Equipment",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    TagNumber = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    Name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    Type = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    Status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false, defaultValue: "Operating"),
                    Capacity = table.Column<double>(type: "double precision", nullable: true),
                    Unit = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    InstallDate = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    UpdatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Equipment", x => x.Id);
                });

            migrationBuilder.InsertData(
                table: "Equipment",
                columns: new[] { "Id", "Capacity", "CreatedAt", "InstallDate", "Name", "Status", "TagNumber", "Type", "Unit", "UpdatedAt" },
                values: new object[,]
                {
                    { 1, 500.0, new DateTime(2025, 11, 16, 15, 46, 23, 946, DateTimeKind.Utc).AddTicks(6635), new DateTime(2020, 1, 15, 0, 0, 0, 0, DateTimeKind.Utc), "Crude Feed Pump", "Operating", "P-101", "Centrifugal Pump", "m³/h", null },
                    { 2, 50.0, new DateTime(2025, 11, 16, 15, 46, 23, 946, DateTimeKind.Utc).AddTicks(6640), new DateTime(2019, 6, 20, 0, 0, 0, 0, DateTimeKind.Utc), "Crude Preheat Exchanger", "Operating", "E-201", "Shell & Tube Heat Exchanger", "MW", null },
                    { 3, 100000.0, new DateTime(2025, 11, 16, 15, 46, 23, 946, DateTimeKind.Utc).AddTicks(6643), new DateTime(2018, 3, 10, 0, 0, 0, 0, DateTimeKind.Utc), "Distillation Column", "Operating", "T-301", "Fractionation Tower", "bbl/day", null }
                });

            migrationBuilder.CreateIndex(
                name: "IX_Equipment_Status",
                table: "Equipment",
                column: "Status");

            migrationBuilder.CreateIndex(
                name: "IX_Equipment_TagNumber",
                table: "Equipment",
                column: "TagNumber",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Equipment_Type",
                table: "Equipment",
                column: "Type");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "Equipment");
        }
    }
}
