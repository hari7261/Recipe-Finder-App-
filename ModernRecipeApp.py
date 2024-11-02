import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import requests
import json
import sqlite3
from datetime import datetime
import re
import io
from typing import List, Dict
import threading

# Set theme and color scheme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class ModernRecipeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("Modern Recipe Finder")
        self.geometry("1400x900")
        
        # API Configuration
        self.API_KEY = ""
        self.BASE_URL = "https://api.spoonacular.com/recipes"
        
        # Initialize database
        self.init_database()
        
        # Create main layout
        self.setup_main_layout()
        
        # Initialize variables
        self.current_recipe_id = None
        self.search_results = []
        
    def init_database(self):
        """Initialize SQLite database"""
        self.conn = sqlite3.connect('recipe_finder.db')
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                recipe_id INTEGER PRIMARY KEY,
                title TEXT,
                image_url TEXT,
                date_added TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS meal_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER,
                planned_date DATE,
                meal_type TEXT
            )
        ''')
        
        self.conn.commit()

    def setup_main_layout(self):
        """Create the main application layout"""
        # Configure grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create sidebar
        self.setup_sidebar()
        
        # Create main content area
        self.setup_main_content()
        
    def setup_sidebar(self):
        """Create sidebar with navigation and filters"""
        # Sidebar frame
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)
        
        # App logo/title
        self.logo_label = ctk.CTkLabel(
            self.sidebar, 
            text="Recipe Finder",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Navigation buttons
        self.nav_buttons = []
        nav_items = [
            ("Search", "🔍"),
            ("Favorites", "⭐"),
            ("Meal Plan", "📅"),
            ("Shopping List", "🛒")
        ]
        
        for idx, (text, icon) in enumerate(nav_items):
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"{icon} {text}",
                font=ctk.CTkFont(size=14),
                height=40,
                corner_radius=8,
                command=lambda t=text: self.handle_navigation(t)
            )
            btn.grid(row=idx+1, column=0, padx=20, pady=10)
            self.nav_buttons.append(btn)
            
        # Filters section
        self.filters_frame = ctk.CTkFrame(self.sidebar)
        self.filters_frame.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        
        # Diet filter
        self.diet_label = ctk.CTkLabel(self.filters_frame, text="Diet Preferences")
        self.diet_label.grid(row=0, column=0, padx=10, pady=5)
        
        self.diet_var = ctk.StringVar(value="None")
        self.diet_menu = ctk.CTkOptionMenu(
            self.filters_frame,
            values=["None", "Vegetarian", "Vegan", "Gluten-Free"],
            variable=self.diet_var,
            dynamic_resizing=False
        )
        self.diet_menu.grid(row=1, column=0, padx=10, pady=5)
        
        # Time filter
        self.time_label = ctk.CTkLabel(self.filters_frame, text="Max Cooking Time")
        self.time_label.grid(row=2, column=0, padx=10, pady=5)
        
        self.time_slider = ctk.CTkSlider(
            self.filters_frame,
            from_=0,
            to=120,
            number_of_steps=12
        )
        self.time_slider.grid(row=3, column=0, padx=10, pady=5)
        
        # Settings and help
        self.settings_btn = ctk.CTkButton(
            self.sidebar,
            text="⚙️ Settings",
            font=ctk.CTkFont(size=14),
            height=40,
            corner_radius=8
        )
        self.settings_btn.grid(row=98, column=0, padx=20, pady=10)
        
        self.help_btn = ctk.CTkButton(
            self.sidebar,
            text="❓ Help",
            font=ctk.CTkFont(size=14),
            height=40,
            corner_radius=8
        )
        self.help_btn.grid(row=99, column=0, padx=20, pady=(10, 20))
        
    def setup_main_content(self):
        """Create the main content area"""
        # Main content frame
        self.main_content = ctk.CTkFrame(self)
        self.main_content.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(1, weight=1)
        
        # Search bar
        self.setup_search_bar()
        
        # Recipe cards container (with scrolling)
        self.setup_recipe_cards_view()
        
    def setup_search_bar(self):
        """Create the search interface"""
        self.search_frame = ctk.CTkFrame(self.main_content)
        self.search_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        # Search entry
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Enter ingredients (comma separated)",
            width=400,
            height=40
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        
        # Search button
        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="Search Recipes",
            width=120,
            height=40,
            command=self.search_recipes
        )
        self.search_button.pack(side="left")
        
    def setup_recipe_cards_view(self):
        """Create scrollable recipe cards container"""
        # Create scrollable frame
        self.recipe_scroll = ctk.CTkScrollableFrame(
            self.main_content,
            label_text="Recipe Results"
        )
        self.recipe_scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
        # Configure grid for cards
        self.recipe_scroll.grid_columnconfigure((0, 1, 2), weight=1)
        
    def create_recipe_card(self, recipe: Dict, row: int, col: int):
        """Create a recipe card widget"""
        card = ctk.CTkFrame(self.recipe_scroll)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Recipe image
        if recipe.get('image'):
            try:
                response = requests.get(recipe['image'])
                img = Image.open(io.BytesIO(response.content))
                img = img.resize((200, 200), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                img_label = ctk.CTkLabel(card, image=photo, text="")
                img_label.image = photo  # Keep a reference
                img_label.pack(padx=10, pady=10)
            except:
                # Fallback if image loading fails
                img_label = ctk.CTkLabel(card, text="[No Image]", height=200)
                img_label.pack(padx=10, pady=10)
        
        # Recipe title
        title_label = ctk.CTkLabel(
            card,
            text=recipe['title'],
            font=ctk.CTkFont(size=16, weight="bold"),
            wraplength=180
        )
        title_label.pack(padx=10, pady=5)
        
        # Quick info
        info_frame = ctk.CTkFrame(card)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        if recipe.get('readyInMinutes'):
            time_label = ctk.CTkLabel(
                info_frame,
                text=f"⏱️ {recipe['readyInMinutes']} min"
            )
            time_label.pack(side="left", padx=5)
            
        if recipe.get('servings'):
            servings_label = ctk.CTkLabel(
                info_frame,
                text=f"👥 Serves {recipe['servings']}"
            )
            servings_label.pack(side="left", padx=5)
        
        # Action buttons
        btn_frame = ctk.CTkFrame(card)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        view_btn = ctk.CTkButton(
            btn_frame,
            text="View Recipe",
            width=90,
            height=30,
            command=lambda: self.show_recipe_details(recipe['id'])
        )
        view_btn.pack(side="left", padx=5)
        
        fav_btn = ctk.CTkButton(
            btn_frame,
            text="♥",
            width=30,
            height=30,
            command=lambda: self.add_to_favorites(recipe)
        )
        fav_btn.pack(side="left", padx=5)
        
    def show_recipe_details(self, recipe_id: int):
        """Show detailed recipe information in a new window"""
        details_window = ctk.CTkToplevel(self)
        details_window.title("Recipe Details")
        details_window.geometry("800x900")
        
        try:
            # Fetch recipe details
            params = {'apiKey': self.API_KEY}
            response = requests.get(f"{self.BASE_URL}/{recipe_id}/information", params=params)
            recipe = response.json()
            
            # Create tabview for organized information
            tabview = ctk.CTkTabview(details_window)
            tabview.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Overview tab
            overview_tab = tabview.add("Overview")
            
            # Title
            ctk.CTkLabel(
                overview_tab,
                text=recipe['title'],
                font=ctk.CTkFont(size=24, weight="bold")
            ).pack(pady=10)
            
            # Quick info
            info_frame = ctk.CTkFrame(overview_tab)
            info_frame.pack(fill="x", pady=10)
            
            ctk.CTkLabel(
                info_frame,
                text=f"⏱️ {recipe.get('readyInMinutes', 'N/A')} minutes"
            ).pack(side="left", padx=10)
            
            ctk.CTkLabel(
                info_frame,
                text=f"👥 Serves {recipe.get('servings', 'N/A')}"
            ).pack(side="left", padx=10)
            
            # Ingredients tab
            ingredients_tab = tabview.add("Ingredients")
            ingredients_text = ctk.CTkTextbox(ingredients_tab)
            ingredients_text.pack(fill="both", expand=True, padx=10, pady=10)
            
            for ingredient in recipe['extendedIngredients']:
                ingredients_text.insert("end", f"• {ingredient['original']}\n")
            
            # Instructions tab
            instructions_tab = tabview.add("Instructions")
            instructions_text = ctk.CTkTextbox(instructions_tab)
            instructions_text.pack(fill="both", expand=True, padx=10, pady=10)
            
            if recipe.get('instructions'):
                clean_instructions = re.sub('<[^<]+?>', '', recipe['instructions'])
                instructions_text.insert("end", clean_instructions)
            else:
                instructions_text.insert("end", "No instructions available.")
            
            # Nutrition tab
            nutrition_tab = tabview.add("Nutrition")
            nutrition_text = ctk.CTkTextbox(nutrition_tab)
            nutrition_text.pack(fill="both", expand=True, padx=10, pady=10)
            
            if recipe.get('nutrition', {}).get('nutrients'):
                for nutrient in recipe['nutrition']['nutrients']:
                    nutrition_text.insert(
                        "end",
                        f"{nutrient['name']}: {nutrient['amount']}{nutrient['unit']}\n"
                    )
            
            # Action buttons
            action_frame = ctk.CTkFrame(details_window)
            action_frame.pack(fill="x", padx=20, pady=10)
            
            ctk.CTkButton(
                action_frame,
                text="Add to Meal Plan",
                command=lambda: self.add_to_meal_plan(recipe_id)
            ).pack(side="left", padx=5)
            
            ctk.CTkButton(
                action_frame,
                text="Generate Shopping List",
                command=lambda: self.generate_shopping_list(recipe_id)
            ).pack(side="left", padx=5)
            
        except Exception as e:
            ctk.CTkLabel(
                details_window,
                text=f"Error loading recipe details: {str(e)}"
            ).pack(pady=20)
            
    def search_recipes(self):
        """Search for recipes based on current inputs"""
        ingredients = self.search_entry.get().strip()
        if not ingredients:
            self.show_error("Please enter ingredients to search for recipes.")
            return
            
        # Show loading indicator
        self.search_button.configure(state="disabled", text="Searching...")
        
        def search_thread():
            try:
                params = {
                    'apiKey': self.API_KEY,
                    'ingredients': ingredients,
                    'number': 9,  # Show 3x3 grid of results
                    'ranking': 2,
                    'ignorePantry': True
                }
                
                if self.diet_var.get() != 'None':
                    params['diet'] = self.diet_var.get().lower()
                
                max_time = int(self.time_slider.get())
                if max_time > 0:
                    params['maxReadyTime'] = max_time
                
                response = requests.get(f"{self.BASE_URL}/findByIngredients", params=params)
                recipes = response.json()
                
                # Clear existing recipe cards
                for widget in self.recipe_scroll.winfo_children():
                    widget.destroy()
                
                # Create recipe cards in a grid
                for i, recipe in enumerate(recipes):
                    row = i // 3  # 3 cards per row
                    col = i % 3
                    self.create_recipe_card(recipe, row, col)
                
                self.search_results = recipes
                
            except Exception as e:
                self.show_error(f"Failed to search recipes: {str(e)}")
            finally:
                # Reset search button
                self.search_button.configure(state="normal", text="Search Recipes")
        
        # Run search in separate thread
        threading.Thread(target=search_thread, daemon=True).start()
    
    def add_to_favorites(self, recipe: Dict):
        """Add a recipe to favorites database"""
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO favorites (recipe_id, title, image_url, date_added) VALUES (?, ?, ?, ?)",
                (recipe['id'], recipe['title'], recipe.get('image', ''), datetime.now())
            )
            self.conn.commit()
            self.show_success(f"Added '{recipe['title']}' to favorites!")
        except Exception as e:
            self.show_error(f"Failed to add to favorites: {str(e)}")
    
    def add_to_meal_plan(self, recipe_id: int):
        """Add a recipe to meal plan"""
        meal_plan_window = ctk.CTkToplevel(self)
        meal_plan_window.title("Add to Meal Plan")
        meal_plan_window.geometry("400x300")
        
        # Date picker (simplified for example)
        date_frame = ctk.CTkFrame(meal_plan_window)
        date_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(date_frame, text="Select Date:").pack(side="left", padx=5)
        
        # Simple date entry (could be enhanced with a calendar widget)
        date_entry = ctk.CTkEntry(date_frame, placeholder_text="YYYY-MM-DD")
        date_entry.pack(side="left", padx=5)
        
        # Meal type selection
        meal_frame = ctk.CTkFrame(meal_plan_window)
        meal_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(meal_frame, text="Meal Type:").pack(side="left", padx=5)
        
        meal_var = ctk.StringVar(value="Dinner")
        meal_type = ctk.CTkOptionMenu(
            meal_frame,
            values=["Breakfast", "Lunch", "Dinner", "Snack"],
            variable=meal_var
        )
        meal_type.pack(side="left", padx=5)
        
        def save_to_meal_plan():
            try:
                date = date_entry.get()
                meal = meal_var.get()
                
                self.cursor.execute(
                    "INSERT INTO meal_plans (recipe_id, planned_date, meal_type) VALUES (?, ?, ?)",
                    (recipe_id, date, meal)
                )
                self.conn.commit()
                
                self.show_success("Added to meal plan!")
                meal_plan_window.destroy()
            except Exception as e:
                self.show_error(f"Failed to add to meal plan: {str(e)}")
        
        # Save button
        ctk.CTkButton(
            meal_plan_window,
            text="Save to Meal Plan",
            command=save_to_meal_plan
        ).pack(pady=20)
    
    def generate_shopping_list(self, recipe_id: int):
        """Generate a shopping list for a recipe"""
        try:
            params = {'apiKey': self.API_KEY}
            response = requests.get(f"{self.BASE_URL}/{recipe_id}/information", params=params)
            recipe = response.json()
            
            shopping_window = ctk.CTkToplevel(self)
            shopping_window.title("Shopping List")
            shopping_window.geometry("500x700")
            
            # Shopping list header
            ctk.CTkLabel(
                shopping_window,
                text=f"Shopping List for {recipe['title']}",
                font=ctk.CTkFont(size=20, weight="bold")
            ).pack(padx=20, pady=10)
            
            # Create scrollable text area
            shopping_text = ctk.CTkTextbox(shopping_window)
            shopping_text.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Add ingredients to list
            for ingredient in recipe['extendedIngredients']:
                shopping_text.insert("end", f"□ {ingredient['original']}\n")
            
            # Export button
            def export_list():
                file_path = "shopping_list.txt"
                with open(file_path, "w") as f:
                    f.write(f"Shopping List for {recipe['title']}\n\n")
                    for ingredient in recipe['extendedIngredients']:
                        f.write(f"□ {ingredient['original']}\n")
                self.show_success(f"Shopping list exported to {file_path}")
            
            ctk.CTkButton(
                shopping_window,
                text="Export List",
                command=export_list
            ).pack(pady=10)
            
        except Exception as e:
            self.show_error(f"Failed to generate shopping list: {str(e)}")
    
    def show_favorites(self):
        """Display favorite recipes"""
        # Clear existing recipe cards
        for widget in self.recipe_scroll.winfo_children():
            widget.destroy()
        
        try:
            # Fetch favorites from database
            self.cursor.execute("SELECT * FROM favorites ORDER BY date_added DESC")
            favorites = self.cursor.fetchall()
            
            if not favorites:
                ctk.CTkLabel(
                    self.recipe_scroll,
                    text="No favorite recipes yet!",
                    font=ctk.CTkFont(size=16)
                ).pack(pady=20)
                return
            
            # Create cards for each favorite
            for i, fav in enumerate(favorites):
                recipe = {
                    'id': fav[0],
                    'title': fav[1],
                    'image': fav[2]
                }
                row = i // 3
                col = i % 3
                self.create_recipe_card(recipe, row, col)
                
        except Exception as e:
            self.show_error(f"Failed to load favorites: {str(e)}")
    
    def show_meal_plan(self):
        """Display meal plan calendar"""
        # Clear main content
        for widget in self.recipe_scroll.winfo_children():
            widget.destroy()
        
        # Create calendar view (simplified)
        calendar_frame = ctk.CTkFrame(self.recipe_scroll)
        calendar_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Fetch meal plans
        try:
            self.cursor.execute("""
                SELECT mp.planned_date, mp.meal_type, f.title 
                FROM meal_plans mp 
                JOIN favorites f ON mp.recipe_id = f.recipe_id 
                ORDER BY mp.planned_date, mp.meal_type
            """)
            meals = self.cursor.fetchall()
            
            if not meals:
                ctk.CTkLabel(
                    calendar_frame,
                    text="No meals planned yet!",
                    font=ctk.CTkFont(size=16)
                ).pack(pady=20)
                return
            
            # Create meal plan display
            for date, meal_type, title in meals:
                meal_frame = ctk.CTkFrame(calendar_frame)
                meal_frame.pack(fill="x", padx=10, pady=5)
                
                ctk.CTkLabel(
                    meal_frame,
                    text=f"{date} - {meal_type}:",
                    font=ctk.CTkFont(weight="bold")
                ).pack(side="left", padx=10)
                
                ctk.CTkLabel(
                    meal_frame,
                    text=title
                ).pack(side="left", padx=10)
                
        except Exception as e:
            self.show_error(f"Failed to load meal plan: {str(e)}")
    
    def handle_navigation(self, section: str):
        """Handle navigation button clicks"""
        if section == "Search":
            self.setup_recipe_cards_view()
        elif section == "Favorites":
            self.show_favorites()
        elif section == "Meal Plan":
            self.show_meal_plan()
        elif section == "Shopping List":
            # Show combined shopping list for all planned meals
            self.show_combined_shopping_list()
    
    def show_combined_shopping_list(self):
        """Show shopping list for all planned meals"""
        shopping_window = ctk.CTkToplevel(self)
        shopping_window.title("Combined Shopping List")
        shopping_window.geometry("600x800")
        
        # Create tabview for organized lists
        tabview = ctk.CTkTabview(shopping_window)
        tabview.pack(fill="both", expand=True, padx=20, pady=20)
        
        # All items tab
        all_tab = tabview.add("All Items")
        all_list = ctk.CTkTextbox(all_tab)
        all_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        # By meal tab
        by_meal_tab = tabview.add("By Meal")
        meal_list = ctk.CTkTextbox(by_meal_tab)
        meal_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        try:
            # Fetch all planned meals
            self.cursor.execute("""
                SELECT mp.planned_date, mp.meal_type, f.title, mp.recipe_id
                FROM meal_plans mp 
                JOIN favorites f ON mp.recipe_id = f.recipe_id 
                ORDER BY mp.planned_date
            """)
            meals = self.cursor.fetchall()
            
            if not meals:
                all_list.insert("end", "No meals planned!\n")
                meal_list.insert("end", "No meals planned!\n")
                return
            
            # Fetch ingredients for each meal
            all_ingredients = {}
            for date, meal_type, title, recipe_id in meals:
                params = {'apiKey': self.API_KEY}
                response = requests.get(f"{self.BASE_URL}/{recipe_id}/information", params=params)
                recipe = response.json()
                
                # Add to by-meal list
                meal_list.insert("end", f"\n{date} - {meal_type}: {title}\n")
                for ingredient in recipe['extendedIngredients']:
                    meal_list.insert("end", f"□ {ingredient['original']}\n")
                    
                    # Add to combined list
                    all_ingredients[ingredient['original']] = all_ingredients.get(ingredient['original'], 0) + 1
            
            # Add to all items list
            for ingredient, count in all_ingredients.items():
                if count > 1:
                    all_list.insert("end", f"□ {ingredient} (x{count})\n")
                else:
                    all_list.insert("end", f"□ {ingredient}\n")
                    
        except Exception as e:
            self.show_error(f"Failed to generate shopping list: {str(e)}")
    
    def show_error(self, message: str):
        """Show error message"""
        messagebox = ctk.CTkToplevel(self)
        messagebox.title("Error")
        messagebox.geometry("400x200")
        
        ctk.CTkLabel(
            messagebox,
            text="⚠️ Error",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=10)
        
        ctk.CTkLabel(
            messagebox,
            text=message,
            wraplength=350
        ).pack(pady=10)
        
        ctk.CTkButton(
            messagebox,
            text="OK",
            command=messagebox.destroy
        ).pack(pady=10)
    
    def show_success(self, message: str):
        """Show success message"""
        messagebox = ctk.CTkToplevel(self)
        messagebox.title("Success")
        messagebox.geometry("400x200")
        
        ctk.CTkLabel(
            messagebox,
            text="✅ Success",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=10)
        
        ctk.CTkLabel(
            messagebox,
            text=message,
            wraplength=350
        ).pack(pady=10)
        
        ctk.CTkButton(
            messagebox,
            text="OK",
            command=messagebox.destroy
        ).pack(pady=10)

if __name__ == "__main__":
    app = ModernRecipeApp()
    app.mainloop()
