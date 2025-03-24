from fpdf import FPDF
import datetime

class PDF(FPDF):
    def footer(self):
        self.set_y(-15)  # Position at 15mm from bottom
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Report generated by Building Performance Assistant on {datetime.datetime.now().strftime('%B %d, %Y')}", ln=True, align='L')



def generate_performance_report(state):
    pdf = PDF()
    diff = {
                'heat_gain': state.get('proposed_heat_gain', 0) - state.get('baseline_heat_gain', 0),
                'energy': state.get('proposed_cooling_energy', 0) - state.get('baseline_cooling_energy', 0),
                'cost': state.get('proposed_cost', 0) - state.get('baseline_cost', 0)
            }
    
    # Start fresh page
    pdf.add_page()

    # Set margins
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)

    # Header - start higher on page
    pdf.set_y(15)  # Move everything up

    # BPA part
    pdf.set_font("Arial", "B", 24)
    pdf.set_text_color(26, 35, 126)  # #1a237e blue
    pdf.cell(20, 10, "BPA", ln=False, align='L')  # Adjust width and height

    # Separator + Rest
    pdf.set_text_color(44, 44, 44)  # #2c2c2c gray
    pdf.set_font("Arial", "", 24)  # Regular weight
    pdf.cell(5, 10, "| Building Performance Assistant", ln=False, align='L')  # More space for separator
    pdf.ln(10)

    # Building Details Section
    pdf.ln(20)
    pdf.set_fill_color(26, 35, 126)
    pdf.set_text_color(26, 35, 126)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Building Specifications", ln=True)
    pdf.ln(2)
    
    # Details content
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(60, 10, "Location:", 0)
    pdf.cell(0, 10, f"{state.get('city', 'N/A')}", ln=True)
    pdf.cell(60, 10, "Window Area:", 0)
    pdf.cell(0, 10, f"{state.get('window_area', 0):,.0f} ft²", ln=True)
    pdf.cell(60, 10, "Proposed SHGC:", 0)
    pdf.cell(0, 10, f"{state.get('shgc', 0)}", ln=True)
    pdf.cell(60, 10, "Proposed U-Value:", 0)
    pdf.cell(0, 10, f"{state.get('u_value', 0)}", ln=True)
    pdf.ln(10)

    # ASHRAE Baseline Comparison
    pdf.set_text_color(26, 35, 126)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "ASHRAE Baseline Comparison", ln=True)
    pdf.ln(2)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(60, 10, "Climate Zone:", 0)
    pdf.cell(0, 10, f"{state.get('ashrae_climate_zone', 'N/A')}", ln=True)
    pdf.cell(60, 10, "Baseline SHGC:", 0)
    pdf.cell(0, 10, f"{state.get('ashrae_shgc', 0)}", ln=True)
    pdf.cell(60, 10, "Baseline U-Value:", 0)
    pdf.cell(0, 10, f"{state.get('ashrae_u_factor', 0)}", ln=True)
    pdf.ln(10)

    # Proposed Building Performance Analysis Section
    pdf.set_text_color(26, 35, 126)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Proposed Building Performance", ln=True)
    pdf.ln(2)

    # Performance content
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(60, 10, "Peak Glass Heat Gain:", 0)
    pdf.cell(0, 10, f"{state.get('proposed_glass_heat_gain', 0):,.0f} BTU/hr", ln=True)
    pdf.cell(60, 10, "Building Energy Use:", 0)
    pdf.cell(0, 10, f"{state.get('proposed_cooling_energy', 0):,.0f} kWh", ln=True)
    pdf.cell(60, 10, "Annual Energy Cost:", 0)
    pdf.cell(0, 10, f"${state.get('proposed_cost', 0):,.2f}", ln=True)
    pdf.ln(10)
    
    # Baseline Building Performance Analysis Section
    pdf.set_text_color(26, 35, 126)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Baseline Building Performance", ln=True)
    pdf.ln(5)

    # Performance content
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(60, 10, "Peak Glass Heat Gain:", 0)
    pdf.cell(0, 10, f"{state.get('baseline_glass_heat_gain', 0):,.0f} BTU/hr", ln=True)
    pdf.cell(60, 10, "Building Energy Use:", 0)
    pdf.cell(0, 10, f"{state.get('baseline_cooling_energy', 0):,.0f} kWh", ln=True)
    pdf.cell(60, 10, "Annual Energy Cost:", 0)
    pdf.cell(0, 10, f"${state.get('baseline_cost', 0):,.2f}", ln=True)
    pdf.cell(60, 10, "Wall Heat Gain:", 0)
    pdf.cell(0, 10, f"{state.get('wall_heat_gain', 0):,.0f} BTU/hr", ln=True)
    pdf.ln(10)

    # Performance Comparison Section
    pdf.ln(10)
    pdf.set_text_color(26, 35, 126)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Performance Comparison Difference", ln=True)
    pdf.ln(5)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 12)

    # Add performance comparison difference metrics
    # First metric - Heat Gain
    pdf.cell(60, 10, "Peak Glass Heat Gain:", 0)
    pdf.cell(0, 10, f" {abs(diff['heat_gain']):,.0f} BTU/hr {'more than baseline' if diff['heat_gain'] > 0 else 'less than baseline'}", ln=True)

    # Second metric - Energy Usage
    pdf.cell(60, 10, "Energy Usage:", 0)
    pdf.cell(0, 10, f" {abs(diff['energy']):,.0f} kWh/year {'more than baseline' if diff['energy'] > 0 else 'less than baseline'}", ln=True)

    # Third metric - Cost Impact
    pdf.cell(60, 10, "Cooling Costs:", 0)
    pdf.cell(0, 10, f" ${abs(diff['cost']):,.2f} {'more than baseline' if diff['cost'] > 0 else 'less than baseline'}", ln=True)

    return pdf.output(dest='S').encode('latin-1')
