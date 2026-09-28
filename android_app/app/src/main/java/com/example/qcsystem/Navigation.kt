package com.example.qcsystem

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.ui.NavDisplay
import com.example.qcsystem.data.DataRepository
import com.example.qcsystem.ui.builder.BuilderScreen
import com.example.qcsystem.ui.screens.ChecksheetScreen
import com.example.qcsystem.ui.screens.DetailsScreen
import com.example.qcsystem.ui.screens.LoginScreen
import com.example.qcsystem.ui.screens.RecordsScreen
import com.example.qcsystem.ui.screens.SelectScreen

@Composable
fun MainNavigation(repository: DataRepository) {
    val backStack = rememberNavBackStack(LoginNavKey)

    NavDisplay(
        backStack = backStack,
        onBack = { backStack.removeLastOrNull() },
        entryProvider = entryProvider {
            entry<LoginNavKey> {
                LoginScreen(
                    repository = repository,
                    onLoginSuccess = {
                        backStack.clear()
                        backStack.add(SelectNavKey)
                    }
                )
            }

            entry<SelectNavKey> {
                SelectScreen(
                    repository = repository,
                    onSelectSheet = { sheetKey ->
                        backStack.add(DetailsNavKey(sheetKey))
                    },
                    onOpenRecords = {
                        backStack.add(RecordsNavKey)
                    },
                    onOpenBuilder = {
                        backStack.add(BuilderNavKey())
                    },
                    onSignOut = {
                        repository.setCurrentUser(null)
                        backStack.clear()
                        backStack.add(LoginNavKey)
                    }
                )
            }

            entry<DetailsNavKey> { navKey ->
                DetailsScreen(
                    repository = repository,
                    checksheetKey = navKey.checksheetKey,
                    onBack = { backStack.removeLastOrNull() },
                    onContinue = { unitFields ->
                        backStack.add(ChecksheetNavKey(navKey.checksheetKey, unitFields))
                    }
                )
            }

            entry<ChecksheetNavKey> { navKey ->
                ChecksheetScreen(
                    repository = repository,
                    checksheetKey = navKey.checksheetKey,
                    unitFields = navKey.unitFields,
                    onFinished = {
                        // Pop back to Select screen
                        while (backStack.size > 1 && backStack.lastOrNull() != SelectNavKey) {
                            backStack.removeLastOrNull()
                        }
                    }
                )
            }

            entry<RecordsNavKey> {
                RecordsScreen(
                    repository = repository,
                    onBack = { backStack.removeLastOrNull() }
                )
            }

            entry<BuilderNavKey> { navKey ->
                BuilderScreen(
                    repository = repository,
                    initialSheetKey = navKey.sheetKey,
                    onBack = { backStack.removeLastOrNull() }
                )
            }
        }
    )
}
